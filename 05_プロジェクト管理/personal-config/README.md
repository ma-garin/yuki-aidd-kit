# personal-config — 個人設定の置き場（本文はコミットしない）

新規マシンでも手元と同じ挙動にするため、リポジトリの外にある個人設定を**一時的に**置く場所。
`.gitignore` が `README.md` と `.gitignore` 以外をすべて無視するので、本文は既定でコミットされない。
版管理したい場合は、保守者が**私有リポジトリ**で行う（このキットのリポジトリには入れない）。

## 置くもの
- `userPreferences.md` — claude.ai の userPreferences（設定 → プロフィールの指示）の本文
- `memory-export/` — Claude のメモリのエクスポート一式

## 置かないもの
- トークン・パスワード・API キー・秘密鍵
- 金銭情報（口座・カード・家計の数値）
- 第三者の個人情報（氏名・連絡先・SNS・評価など）

## 取り出し手順（旧マシン → ここ）
1. claude.ai の userPreferences 本文をコピーし、`userPreferences.md` に貼る
2. メモリをエクスポートし、`memory-export/` に展開する
3. 下の「コミット前の確認」を行う（コミットしない場合も、私有リポジトリへ移す前に行う）

## 戻し手順（ここ → 新マシン）
1. `userPreferences.md` の本文を claude.ai の userPreferences に貼り戻す
2. `memory-export/` をメモリの取り込み（import）で戻す
3. `python3 00_導入/03_点検/doctor.py` で全緑を確かめる
4. 戻し終えたら、このディレクトリの本文を消す（残すなら私有リポジトリへ）

## コミット前の確認（私有リポジトリへ移す場合も同じ）
1. `bash 02_共通/ツール/security-scan.sh 05_プロジェクト管理/personal-config` を実行し、秘密の検出が 0 件であること
2. 目視で、上の「置かないもの」（秘密・金銭情報・第三者の個人情報）が入っていないことを確かめる
3. `git status --ignored 05_プロジェクト管理/personal-config/` で本文が ignored 側にあることを確かめる
