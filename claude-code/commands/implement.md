# /implement — 実装モードの開始（探索ブロックON）

引数: $ARGUMENTS（任意: 実装対象の補足メモ）

## 実行内容

plan 確定後の実装フェーズに入る。再探索（Read/Grep/Glob）を物理ブロックし、確定済みの方針・対象ファイルの実装に集中する。

1. **plan の存在を確認**（必須ゲート）
   - `PLAN.md`（または `docs/plan.md` / `.claude/plan.md` などプロジェクトの plan ファイル）が存在するか確認する
   - **存在しなければ警告して中断**する。「plan が未作成です。先に /plan で方針を確定してください」と表示し、`.claude/mode` は作成しない
2. **実装モードを有効化**
   - `mkdir -p .claude && echo "implement" > .claude/mode`
   - 以降 `block-explore.sh` hook が Read / Grep / Glob をブロックする
3. **実装プロファイルを適用**
   - `templates/implement-profile.md` の行動規範（再探索しない・plan準拠・小さく実装→軽量テスト・done-gate）に従う
4. 実装完了後は done-gate で完了判定し、`/plan` で実装モードを解除する

**plan が存在する場合のみ `.claude/mode` を作成すること。** plan 未作成で実装モードに入ってはいけない。
