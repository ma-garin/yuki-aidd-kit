#!/usr/bin/env bash
# Claude Code ステータスライン（macOS / Linux / Windows Git Bash 共通）
# 外部コマンドは jq 1 回（＋60 秒に 1 回の curl）に絞る。Windows はプロセス起動が 1 回 100〜300ms かかり、
# 項目ごとに jq を呼ぶ旧版は 7 秒を超えて statusline.py の 5 秒制限で 2〜4 行目が消えた（2026-11-03 実測）
input=$(cat)
printf -v now '%(%s)T' -1
T="${TMPDIR:-/tmp}"
EMPTY="$T/claude-sl-empty"; [ -f "$EMPTY" ] || : > "$EMPTY"

oauth_token() {
  if [[ $OSTYPE == darwin* ]]; then
    security find-generic-password -s "Claude Code-credentials" -w 2>/dev/null | jq -r '.claudeAiOauth.accessToken // empty'
  else
    local cred re='"accessToken"[[:space:]]*:[[:space:]]*"([^"]+)"'
    [ -f "$HOME/.claude/.credentials.json" ] || return
    IFS= read -r -d '' cred < "$HOME/.claude/.credentials.json"
    [[ $cred =~ $re ]] && printf '%s' "${BASH_REMATCH[1]}"
  fi
}

# Fable 専用枠（OAuth usage API、60 秒キャッシュ）。取得は裏で走らせ、描画は手元のキャッシュで即返す
# （取得の待ちで描画が止まらない。最新値は次の描画で出る）。取得時刻は stat を使わず別ファイルに持つ
FABLE_CACHE="$T/claude-fable-usage.json"; FABLE_TS="$FABLE_CACHE.ts"
last=0; [ -f "$FABLE_TS" ] && read -r last < "$FABLE_TS"
if [ $((now - ${last:-0})) -ge 60 ]; then
  printf '%s\n' "$now" > "$FABLE_TS"
  (
    tok=$(oauth_token)
    if [ -n "$tok" ] && curl -s -m 3 -H "Authorization: Bearer $tok" -H "anthropic-beta: oauth-2025-04-20" \
         https://api.anthropic.com/api/oauth/usage -o "$FABLE_CACHE.tmp"; then
      IFS= read -r -d '' body < "$FABLE_CACHE.tmp"
      if [[ $body == *'"limits"'* ]]; then mv -f "$FABLE_CACHE.tmp" "$FABLE_CACHE"; else rm -f "$FABLE_CACHE.tmp"; fi
    fi
  ) </dev/null >/dev/null 2>&1 &
  disown 2>/dev/null
fi
fcf=$FABLE_CACHE; [ -f "$FABLE_CACHE" ] || fcf=$EMPTY

# 状態（処理中・待機）は出さない（2026-10-06 保守者の指定）ので計算もしない
read -r -d '' PROG <<'JQ'
def bar: ((. // 0) | floor) as $p | [range(10) | if . < ($p / 10 | floor) then "●" else "○" end] | join("");
def toe: if type == "number" then . elif type == "string" then (sub("\\.[0-9]+"; "") | sub("(Z|[+-]00:?00)$"; "") + "Z" | fromdateiso8601) else null end;
def ft: (toe? // null) as $e | if $e == null then "-" else ($e | strflocaltime("%m/%d %H:%M")) end;
def rate($label; $w): if ($w.used_percentage // null) == null then "\($label) (n/a)"
  else "\($label) \($w.used_percentage | bar) \($w.used_percentage | floor)% ↻\($w.resets_at | ft)" end;
($now | tonumber) as $now
| ($fc | try fromjson catch null) as $fcj
| ([$fcj.limits[]? | select(.scope.model.display_name == "Fable")] | first) as $fb
| (.effort.level // "") as $effort
| (if .prompt_cache.warm == true then
     ((.prompt_cache.expires_at | toe?) // null) as $e
     | if $e != null and $e > $now then "cache \(($e - $now) / 60 | floor)m" else "cache on" end
   elif .prompt_cache.warm == false then "cache -"
   else "" end) as $cache
| ((.workspace.current_dir // .cwd // "") | gsub("\\\\"; "/") | split("/") | last // "") as $dirname
| "\(.model.display_name // "unknown") \(if $effort == "" then "?" else $effort end) | \($dirname)\(if $cache != "" then " | \($cache)" else "" end)",
  rate("current"; .rate_limits.five_hour // {}),
  rate("weekly "; .rate_limits.seven_day // {}),
  (if $fb.percent != null
   then "fable   \($fb.percent | bar) \($fb.percent | floor)% ↻\($fb.resets_at | ft)\(if $effort == "xhigh" and $fb.percent >= 80 then "   ⚠ effort=xhigh" else "" end)"
   else "fable   (n/a)" end)
JQ
# プログラムは引数でなくファイルで渡す（Windows ネイティブ jq への非 ASCII 引数の化けを避ける）
PF="$T/claude-sl.jq"; printf '%s' "$PROG" > "$PF"
jqopt=(-r); [[ $OSTYPE == msys* || $OSTYPE == cygwin* ]] && jqopt+=(-b)
jq "${jqopt[@]}" --arg now "$now" --rawfile fc "$fcf" -f "$PF" <<<"$input"
