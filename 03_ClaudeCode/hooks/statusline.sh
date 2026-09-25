#!/usr/bin/env bash
# Claude Code ステータスライン（macOS / Linux / Windows Git Bash 共通）
input=$(cat)
j() { echo "$input" | jq -r "$1"; }

case "$(uname -s)" in Darwin) OS=mac ;; *) OS=other ;; esac
mtime() { if [ "$OS" = mac ]; then stat -f %m "$1"; else stat -c %Y "$1"; fi; }
fmt_epoch() { if [ "$OS" = mac ]; then date -r "$1" "+%m/%d %H:%M"; else date -d "@$1" "+%m/%d %H:%M"; fi; }
iso_to_epoch() { if [ "$OS" = mac ]; then TZ=UTC date -j -f "%Y-%m-%dT%H:%M:%S" "${1%%.*}" +%s 2>/dev/null; else date -d "$1" +%s 2>/dev/null; fi; }
oauth_token() {
  if [ "$OS" = mac ]; then
    security find-generic-password -s "Claude Code-credentials" -w 2>/dev/null | jq -r '.claudeAiOauth.accessToken // empty'
  else
    jq -r '.claudeAiOauth.accessToken // empty' "$HOME/.claude/.credentials.json" 2>/dev/null
  fi
}

model=$(j '.model.display_name // "unknown"')
dir=$(j '.workspace.current_dir // .cwd // ""')
effort=$(j '.effort.level // empty')
ctx=$(j '.context_window.used_percentage // 0' | cut -d. -f1)
ctx_left=$(j '((.context_window.context_window_size // 0) * (.context_window.remaining_percentage // 0) / 100 / 1000) | floor')
over200k=$(j '.exceeds_200k_tokens // false')
five=$(j '.rate_limits.five_hour.used_percentage // 0' | cut -d. -f1)
week=$(j '.rate_limits.seven_day.used_percentage // 0' | cut -d. -f1)
five_reset=$(j '.rate_limits.five_hour.resets_at // empty')
week_reset=$(j '.rate_limits.seven_day.resets_at // empty')
cache_warm=$(j '.prompt_cache.warm // empty')
cache_exp=$(j '.prompt_cache.expires_at // empty')
tpath=$(j '.transcript_path // empty')

bar() {
  pct=${1:-0}; filled=$((pct / 10)); out=""
  i=0; while [ $i -lt 10 ]; do if [ $i -lt $filled ]; then out="${out}●"; else out="${out}○"; fi; i=$((i+1)); done
  echo "$out"
}
fmt_time() { if [ -z "$1" ] || [ "$1" = "null" ]; then echo "-"; else fmt_epoch "$1"; fi; }

# 処理中 / 待機（会話ログの最後の応答が end_turn なら待機）
state="待機"
if [ -n "$tpath" ] && [ -f "$tpath" ]; then
  age=$(( $(date +%s) - $(mtime "$tpath") ))
  last=$(tail -n 200 "$tpath" | jq -R -r 'fromjson? | select(.type=="assistant" or .type=="user") | [.type, (.message.stop_reason // "")] | join(":")' 2>/dev/null | tail -1)
  case "$last" in
    assistant:end_turn|assistant:stop_sequence) ;;
    *) [ "$age" -lt 600 ] && state="処理中" ;;
  esac
  if [ "$state" = "処理中" ]; then
    uts=$(tail -n 400 "$tpath" | jq -R -r 'fromjson? | select(.type=="user") | select((.message.content|type)=="string" or ((.message.content|type)=="array" and (.message.content[0].type? // "")=="text")) | .timestamp' 2>/dev/null | tail -1)
    ue=$(iso_to_epoch "$uts")
    if [ -n "$ue" ]; then
      el=$(( $(date +%s) - ue ))
      if [ "$el" -ge 60 ]; then state="処理中 $((el/60))m$((el%60))s"; else state="処理中 ${el}s"; fi
    fi
  fi
fi

# Fable 専用枠（OAuth usage API、60 秒キャッシュ）
FABLE_CACHE="${TMPDIR:-/tmp}/claude-fable-usage.json"
fable_fetch() {
  now=$(date +%s)
  if [ -f "$FABLE_CACHE" ] && [ $((now - $(mtime "$FABLE_CACHE"))) -lt 60 ]; then return; fi
  tok=$(oauth_token); [ -z "$tok" ] && return
  tmp=$(mktemp)
  if curl -s -m 3 -H "Authorization: Bearer $tok" -H "anthropic-beta: oauth-2025-04-20" \
       https://api.anthropic.com/api/oauth/usage -o "$tmp" && jq -e '.limits' "$tmp" >/dev/null 2>&1; then
    mv "$tmp" "$FABLE_CACHE"
  else
    rm -f "$tmp"
  fi
}
fable_fetch
fable_pct=""; fable_reset=""
if [ -f "$FABLE_CACHE" ]; then
  fable_pct=$(jq -r '[.limits[]? | select(.scope.model.display_name=="Fable")][0].percent // empty' "$FABLE_CACHE" | cut -d. -f1)
  iso=$(jq -r '[.limits[]? | select(.scope.model.display_name=="Fable")][0].resets_at // empty' "$FABLE_CACHE")
  [ -n "$iso" ] && fable_reset=$(iso_to_epoch "$iso")
fi

cache=""
if [ "$cache_warm" = "true" ]; then
  left=""
  if [ -n "$cache_exp" ] && [ "$cache_exp" != "null" ]; then
    secs=$((cache_exp - $(date +%s))); [ "$secs" -gt 0 ] && left=" $((secs/60))m"
  fi
  cache="cache${left:- on}"
elif [ "$cache_warm" = "false" ]; then
  cache="cache -"
fi
branch=$(git -C "$dir" branch --show-current 2>/dev/null); [ -z "$branch" ] && branch="-"

line1="${model} ${effort:-?} | ${dir##*/}"
echo "$line1"
echo "current $(bar "$five") ${five}% ↻$(fmt_time "$five_reset")"
echo "weekly  $(bar "$week") ${week}% ↻$(fmt_time "$week_reset")"
warn=""; [ "$effort" = "xhigh" ] && [ -n "$fable_pct" ] && [ "$fable_pct" -ge 80 ] && warn="   ⚠ effort=xhigh"
if [ -n "$fable_pct" ]; then echo "fable   $(bar "$fable_pct") ${fable_pct}% ↻$(fmt_time "$fable_reset")${warn}"; else echo "fable   (n/a)"; fi
