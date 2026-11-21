# I5-skills 段2（深掘り・再現）

- 入力: `docs/research/2026-11-21/stage1/I5-skills.md`（Critical 0・High 2・Medium 5・Low 7）
- 選んだ件: Critical が無いため High の 2 件すべて（I5-skills-01、I5-skills-02）。「最大 3 件」だが High は 2 件しか無い
- 実行場所: worktree `research-20261121`（以下 `$R`）。読むだけ。生成スクリプトは出力先を消して書き直す（`shutil.rmtree(out)`）ので実行せず、関数だけを import して呼んだ
- 実施日時: 2026-11-21 16:49 以降（Asia/Tokyo）

```sh
R=/Users/fujimagariyuki/dev/active/04_AI開発基盤/yuki-aidd-kit/.claude/worktrees/research-20261121
```

---

## I5-skills-01 Codex 版の `cmd-*` 25 件がすべて暗黙発火可

- 深刻度: High（段1のまま維持）
- 判定: **再現**（生成物の集計・生成ロジックの経路・関数の単体実行）。Codex 実機での誤発火は未実行（Codex 環境なし）

### 再現手順

```sh
cd $R
# 1. 生成物の集計
for f in 04_Codex/skills/cmd-*/agents/openai.yaml; do grep -h allow_implicit "$f"; done | sort | uniq -c
ls -d 04_Codex/skills/cmd-* | wc -l
# 2. 元のコマンドに frontmatter があるか
grep -ln "^---" 03_ClaudeCode/commands/*.md | wc -l ; ls 03_ClaudeCode/commands/*.md | wc -l
# 3. 生成ロジック
grep -n "def write_skill" -A8 04_Codex/build_codex_skills.py
sed -n 145,152p 04_Codex/build_codex_skills.py
# 4. frontmatter 解析を単体で呼ぶ（スクリプト本体は実行しない）
cd 04_Codex && python3 -I -c "
import importlib.util
s=importlib.util.spec_from_file_location('b','build_codex_skills.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
for t in ['# /x — t\nbody','---\ndisable-model-invocation: true\ndescription: d\n---\n# /x\n']:
  fm,b=m.frontmatter(t); print(repr(fm),'implicit=',fm.get('disable-model-invocation','').lower()!='true')"
# 5. skill-lint が cmd-* を見るか
cd $R && python3 -I 02_共通/ツール/skill-lint.py | tail -2
```

### 実測結果

| 測ったもの | 結果 |
|---|---|
| `cmd-*` の数 | 25 |
| `allow_implicit_invocation` | true 25 / false 0 |
| frontmatter 付きコマンド | 0 / 25 |
| skill-lint | NG=0（cmd-* は対象外） |

- 段1の説明より原因が一段深い。段1は `build_codex_skills.py:135` の `implicit = fm.get("disable-model-invocation", ...)` を原因としたが、これはスキル（`sources`）用のループ。**コマンド用のループ（`:151`）は `write_skill(..., f"/{cmd.stem}")` で `implicit` 引数を渡していない**ため、`write_skill` の既定値 `implicit: bool = True`（`:69`）で常に true になる。コマンドの先頭に `disable-model-invocation: true` を書いても、今の生成ロジックでは false にならない（`:151` が fm のその項目を読まないため。読解による。生成の実行はしていない）
- 単体実行: frontmatter 無しの入力 → `{} implicit= True`、`disable-model-invocation: true` 付き → `implicit= False`。この判定はスキル側の経路だけにある
- 自動で起動しうる代表例（各 `04_Codex/skills/cmd-<名>/agents/openai.yaml:5` が `allow_implicit_invocation: true`）:
  - `cmd-implement`「/implement — 実装モードの開始（探索ブロックON）」→ 実装モードに入る操作が明示なしに走りうる
  - `cmd-ralph`「/ralph — 完了の合言葉が出るまで同じ依頼を回し直す（opt-in の完了ループ）」→ opt-in と書きながら暗黙発火可
  - `cmd-security-audit` → 本体 `03_ClaudeCode/skills/security-audit/SKILL.md:3` は「明示に依頼された時と /security-audit で使う」「ecc-daily-router からは自動で振らない」
  - `cmd-retro` と `retro`（`04_Codex/skills/retro/agents/openai.yaml:5` も true）が同じ発火候補で重なる
- 検査で見つからない理由: `02_共通/ツール/skill-lint.py:17-18,103-110` の S7 は `--skills`（既定は CC 版 27 件）の各スキルについて Codex 版を照合するだけで、`cmd-*` は一覧に無いので照合されない。実行結果は `OK: スキル 27 件・NG=0 WARN=1（Codex 照合: あり）`
- 直し方（実装はしていない）: `:151` で `implicit=False`（またはコマンドの frontmatter を読む）を渡し、skill-lint に `04_Codex/skills/cmd-*` の S7 照合を足す

---

## I5-skills-02 デバイス方針がスキル間で食い違う（PC のみ ／ 360px 必須）

- 深刻度: High → **Medium に下げる**（下記の通り、段1の「nfr-standards は PWA に限定していない」は誤り。食い違いは単一HTMLツールと完了条件の 2 か所に絞られる）
- 判定: **再現**（範囲を狭めて。両側の行を引用）

### 再現手順

```sh
cd $R
grep -n "PC のみ\|モバイル対応を独立" 03_ClaudeCode/skills/design-system/SKILL.md
grep -n "^#" 03_ClaudeCode/skills/nfr-standards/SKILL.md | sed -n 1,8p
sed -n 27,32p 03_ClaudeCode/skills/nfr-standards/SKILL.md
sed -n 21,27p 03_ClaudeCode/skills/test-automation/SKILL.md
grep -Hn "狭い画面・モーダル" ~/.claude/AGENTS.md
```

### 実測結果（引用）

PC 側:
- `03_ClaudeCode/skills/design-system/SKILL.md:67`「検証幅は **1366×768 / 1920×1080（PC のみ）**。360・768 の確認と off-canvas は利用者が明示したときだけ行う」
- 同 `:143`「保守者の明示指示がない限り、作るシステムはPCでの操作を前提とする。…モバイル対応を独立した要件として追加しない。狭い画面・タッチ操作の確認は利用者が明示したときだけ行う（2026-11-15 利用者方針…）」

360px 側:
- `03_ClaudeCode/skills/nfr-standards/SKILL.md:28`「折りたたみAndroid端末 カバー画面: 360×820px で主要機能が使えること」・`:31`「タッチターゲット: 44×44px以上」。ただし見出しは `:20 ## NFR: PWA（personal accounting PWA / nichijo系）` の下で、単一HTML（`:54`）・Streamlit（`:71`）の節には 360px の記述が無い → **段1の「PWA に限定していない」は誤り**。PWA は personal-pwa が「スマホ向けUI」を前提にする種別で、design-system の「明示指示がない限り」の例外として読める
- `03_ClaudeCode/skills/test-automation/SKILL.md:21`「## Playwright（PWA/HTML）の最小スモーク観点」の下 `:26`「折りたたみ端末カバー幅（360px）でレイアウトが崩れない（viewport指定）」→ **単一HTMLツールにも 360px を課す**。design-system の PC 既定と食い違う（残る矛盾 1）
- `~/.claude/AGENTS.md:103`「UI を触ったら `uiux_review` で全状態（通常・実行中・失敗・0件・**狭い画面**・モーダル）を実機で開いてから報告する」→ 全 UI に狭い画面の確認を課す完了条件。design-system `:143` の「利用者が明示したときだけ」と食い違う（残る矛盾 2。kit 外の利用者設定のため kit 側の真実源は未確認）
- 変更日: design-system は `7e80b79`（#133）で PC 既定。nfr-standards・test-automation の最終変更は `383577a`（2026-11-14）で、2026-11-15 の方針より前（`git log -1 -- <file>`）。方針変更が下流へ反映されていない時系列と合う

---

## 段1からの修正点

- I5-skills-01: 原因箇所を `:135`（スキル側）から `:151`＋`:69`（コマンド側で引数を渡さず既定 True）へ訂正。frontmatter を足すだけでは直らない
- I5-skills-02: nfr-standards の 360px は PWA 節に限定されていた。食い違いは test-automation の「PWA/HTML」節と AGENTS.md の完了条件の 2 か所。深刻度 Medium
