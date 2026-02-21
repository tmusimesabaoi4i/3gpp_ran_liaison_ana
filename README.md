# 3GPP RAN TDoc List パイプライン

3GPP RAN Plenary の TDoc List（Excel）を範囲指定で一括ダウンロードし、Liaison（LS in/out）だけを正規化して Sankey 図で可視化するまでを一連のパイプラインで実行できます。

**入口スクリプトは build_liaison_html.py（ラッパ）** です。同名の旧版/派生版が混在すると、不具合が「直っていない」ように見える事故が起きます。必ずこのラッパ経由で viewer を生成してください。

---

## 目次

- [Install（環境構築）](#install環境構築)
- [Quickstart](#quickstart)
- [Tools（スクリプト一覧）](#toolsスクリプト一覧)
  - [.py の使い方](#py-の使い方実行時の詳細なconfig)
- [出力物のスキーマ](#出力物のスキーマ)
- [実行手順（Step 0〜5）](#実行手順step-05)
- [Troubleshooting](#troubleshooting)
- [コーディング規約](#コーディング規約)
- [Notes](#notes)

---

## Install（環境構築）

- **Python 3.10+** 推奨（3.9+ でも動作）
- 依存: `requests`（DL）、`pandas`・`openpyxl`（Excel）、`beautifulsoup4`（推奨・未導入時は正規表現フォールバック）

```bash
pip install -r requirements.txt
```

`requirements.txt` の中身例: `requests`, `beautifulsoup4`, `pandas`, `openpyxl`

---

## Quickstart

以下をコピペで実行すると、**90〜110 会合**の TDoc List を取得し、正規化 Excel と Sankey HTML まで一通り生成できます（約 2〜3 分、ネットワーク必要）。

```bash
# 1) 依存インストール
pip install -r requirements.txt

# 2) 90〜110 をダウンロード（TSGR_n と TSGR_ne を自動探索）
python download_ran_tdoc_lists.py --range 90-110 --outdir out/raw_90_110 --overwrite

# 3) manifest から files.txt を生成（手作業禁止推奨）
python manifest_to_files_txt.py out/raw_90_110/manifest.csv

# 4) 正規化 Liaison Excel を生成
python build_liaison_excel.py --list out/raw_90_110/files.txt --out out/liaison_90_110.xlsx

# 5) Sankey viewer を生成（viewer フォルダ）
python build_liaison_html.py --input out/liaison_90_110.xlsx --outdir out/viewer_90_110 --precision 6 --debug
```

**開き方**: `out/viewer_90_110/` 直下で `python -m http.server 8000` を起動し、ブラウザで **http://localhost:8000/index.html** を開く。file:// 直開きは環境により挙動差が出るため、ローカルサーバ推奨。

**UI で確認する最低限**:

- **Direction**: all のときは **左＝Inbound（LS in）・右＝Outbound（LS out）の二面表示**
- **Meeting**: all / #90 … / #110 のラジオで会合フィルタ
- **Split LS out by recipients (1/k)**: ON にすると、LS out の To が複数ある場合に 1/k ずつ配分
- **フロー（リンク）をクリック** → モーダルで from/to/dir と会合別内訳を表示

---

## Tools（スクリプト一覧）

| 役割 | ツール | 入力 | 出力 |
|------|--------|------|------|
| DL | **download_ran_tdoc_lists.py** | `--range`, `--outdir` | outdir 内 xlsx + manifest.csv |
| manifest 補助 | **manifest_to_files_txt.py** | manifest.csv | files.txt |
| 正規化 | **build_liaison_excel.py** | `--list`, `--out` | liaison.xlsx |
| **viewer 入口** | **build_liaison_html.py**（ラッパ） | `--input`, `--outdir` | **viewer フォルダ** |
| 内部（データ） | **build_liaison_data.py** | liaison.xlsx | data.js, edges_by_meeting.csv, edges_total.csv（edge_key 付き） |
| 内部（テンプレ） | **build_liaison_template.py** | — | index.html, viewer.css, app.js |
| 内部（編集点） | **util/viewer_template_builder.py** | — | JS/CSS/HTML 生成の唯一の編集点 |

`build_liaison_html.py` はオーケストレーター（薄いラッパ）で、`--precision` / `--debug` を受け、データ生成 → テンプレ生成を順に呼びます。viewer フォルダの内部は **データ生成（build_liaison_data）** と **テンプレ生成（build_liaison_template → ViewerTemplateBuilder）** に分割されています。UI/動作を変える時は **viewer_template_builder.py** を修正して再生成してください（build_liaison_template.py は「生成コマンド」であり編集点ではありません）。

### .py の使い方（実行時の詳細なconfig）

#### download_ran_tdoc_lists.py

| オプション | 説明 | デフォルト |
|-----------|------|------------|
| `--range` | 会合番号範囲（例: 90-110） | **必須** |
| `--outdir` | 出力フォルダ | **必須** |
| `--manifest` | 取得結果 CSV のパス | `<outdir>/manifest.csv` |
| `--sleep` | リクエスト間スリープ（秒） | 0.2 |
| `--timeout` | HTTP タイムアウト（秒） | 30 |
| `--overwrite` | 既存 xlsx を上書き | オフ |

#### manifest_to_files_txt.py

```bash
python manifest_to_files_txt.py out/raw_90_110/manifest.csv
# → out/raw_90_110/files.txt が生成される
python manifest_to_files_txt.py out/raw_90_110/manifest.csv -o out/custom_files.txt
```

- `-o` / `--output`: 出力 files.txt のパス（省略時は manifest と同じディレクトリの files.txt）

#### build_liaison_excel.py

- `--list`: 入力ファイルリスト（1 行 1 パス、必須）
- `--out`: 出力 Excel パス（必須）

#### build_liaison_html.py

- `--input`: 正規化 Liaison Excel（必須）
- `--outdir`: 出力 viewer フォルダ（必須）
- `--precision`: weight_split の丸め桁数（省略可）
- `--debug`: app.js にデバッグログを埋め込む

---

## 出力物のスキーマ

### manifest.csv

- **列**: `meeting`, `chosen_folder`, `url`, `status`, `http_status`, `saved_path`, `bytes`
- **status**: `OK`（成功）, `SKIPPED_EXISTS`（既存のためスキップ）, `NOT_FOUND`（Docs なし/HTML 失敗）, `NO_TDOC_LIST`（Docs はあるが TDoc List なし）, `DOWNLOAD_ERROR`（HTTP エラー等）

### liaison.xlsx（liaison シート）

- **列**: `RAN`, `Source`, `Type`, `To`
- **正規化ルール**: Type=LS in → To は必ず `RAN`。Type=LS out → Source は必ず `RAN`。
- **e会合の RAN 表記**: ファイル名が `TDoc_List_Meeting_RAN#90-e.xlsx` でも、**RAN 列は #&lt;数字&gt; に統一**（例: `#90`）。通常会合も e 会合も `#90`, `#109` のように数字のみのラベルで扱う。

### viewer フォルダ（6 ファイル）

内部は **データ生成（build_liaison_data）** と **テンプレ生成（build_liaison_template）** に分割。編集は `viewer_template_builder.py` で行い、生成物は手で直さないこと。

- **index.html** — UI コンテナ。Direction / Meeting / Split トグル、Sankey 描画、モーダル。
- **app.js** — 描画ロジック（二面表示・split 重み・クリック→モーダル）。
- **data.js** — `window.LIAISON_DATA`（meetings, edgesByMeeting, edgesTotal）。ローカル `file://` でも fetch 不要で動作。
- **viewer.css** — コントロール・凡例・モーダルのスタイル。
- **edges_by_meeting.csv** — 会合別エッジ集計。列: `meeting`, `dir`, `from`, `to`, `edge_key`, `raw_count`, `weight_raw`, `weight_split`。モーダルの会合別内訳に使用。
- **edges_total.csv** — 会合を集約したエッジ。列: `dir`, `from`, `to`, `edge_key`, `raw_count`, `weight_raw`, `weight_split`。

**編集ポリシー**: `out/viewer_*/` 配下は **生成物**（原則コミットしない／手で直さない）。UI/動作を変える時は **viewer_template_builder.py** を修正して再生成する。

**表示方針（なぜ二面表示か）**: All のときは左に Inbound（Source→RAN）、右に Outbound（RAN→To）の 2 本の Sankey を並べる構成にしている（中央 1 本だと in/out の太さ誤解を招きやすいため）。

---

## 実行手順（Step 0〜5）

**前提**: 作業ディレクトリ直下に各 .py がある（download_ran_tdoc_lists.py, manifest_to_files_txt.py, build_liaison_excel.py, build_liaison_html.py, build_liaison_data.py, build_liaison_template.py, util/viewer_template_builder.py）。

- **Step 0（クリーンアップ・必須）**  
  前回生成物の取り違えを防ぐため、**必ず削除してから開始**する。

  ```powershell
  # Windows PowerShell
  Remove-Item -Recurse -Force out\raw_90_110,out\viewer_90_110 -ErrorAction SilentlyContinue
  Remove-Item -Force out\liaison_90_110.xlsx -ErrorAction SilentlyContinue
  New-Item -ItemType Directory -Force out | Out-Null
  ```

  ```bash
  # Unix / bash
  rm -rf out/raw_90_110 out/viewer_90_110 out/liaison_90_110.xlsx
  mkdir -p out
  ```

- **Step 1（DL）**  
  `python download_ran_tdoc_lists.py --range 90-110 --outdir out/raw_90_110 --overwrite`  
  **合格判定**: `out/raw_90_110/manifest.csv` が生成される。manifest の bytes > 0 が多数（0 が多いなら DL 失敗扱い）。期待行数は 21 行（90〜110）。e会合の chosen_folder は `.../TSGR_{n}e/Docs/` を指す（90, 91, 92, 93, 94, 95, 97, 98）。通常会合（96, 99〜110）は `.../TSGR_{n}/Docs/`。

- **Step 2（manifest → files.txt）**  
  `python manifest_to_files_txt.py out/raw_90_110/manifest.csv`  
  **合格判定**: `out/raw_90_110/files.txt` が生成され、中身が空でない（複数行ある）。

- **Step 3（正規化）**  
  `python build_liaison_excel.py --list out/raw_90_110/files.txt --out out/liaison_90_110.xlsx`  
  **合格判定**: `out/liaison_90_110.xlsx` ができる。liaison シートがあり、列が RAN, Source, Type, To である。

- **Step 4（viewer 生成）**  
  `python build_liaison_html.py --input out/liaison_90_110.xlsx --outdir out/viewer_90_110 --precision 6 --debug`  
  内部的に `build_liaison_data.py` が edges_*.csv / data.js を、`build_liaison_template.py` が index.html / viewer.css / app.js を生成。  
  **合格判定**: `out/viewer_90_110/` に index.html, app.js, viewer.css, data.js, edges_total.csv, edges_by_meeting.csv の 6 ファイルが揃うこと。**不足があれば即 NG**（生成フローが途中で止まっている）。

- **Step 5（ブラウザ起動）**  
  `cd out/viewer_90_110` のうえで `python -m http.server 8000` を実行し、ブラウザで **http://localhost:8000/index.html** を開く。

### 確認項目（回帰チェック）

Step 5 で開いた viewer において、以下で Problem1/2 の潰し込みを確認する。

| 項目 | 合格条件 |
|------|----------|
| **500m が出ない（Problem2）** | Meeting=#100、Direction=all、Split ON で、RAN→SA のフローにマウスオーバーしたとき、hover が "500m" でなく `0.50` のような固定小数表示になる。 |
| **リンククリックでモーダルが開く（Problem1）** | Sankey の**線（リンク）**をクリックするとモーダルが開く。`--debug` 時は Console に edgeKey が出る。 |
| **ノードクリックではモーダルが出ない** | ノード（RAN や SA）をクリックしてもモーダルは開かない。 |

---

## Troubleshooting

| 現象 | 確認・対処 |
|------|------------|
| **NOT_FOUND / NO_TDOC_LIST** | manifest の該当行の url をブラウザで開き、Docs 一覧とファイル名（e会合は `TDoc_List_Meeting_RAN#90-e.xlsx` 形式）が想定どおりか確認。 |
| **HTTP_403 / 404** | 一時的な制限の可能性。`--sleep 1` などで負荷を下げて再実行。 |
| **企業 NW・プロキシ** | `HTTPS_PROXY` / `HTTP_PROXY` を設定してから実行。 |
| **build_liaison_excel が落ちる** | 該当 xlsx に **TDoc_List** シートと列 **Source, Type, To** があるか確認。 |
| **古い app.js を見ている** | HTML は出るが UI が変／クリックしてもモーダルが出ない場合、まず古い生成物を疑う。`app.js` に `hovertemplate` と `chartEl.on("plotly_click"` が無いなら再生成が必要。該当 viewer フォルダを削除し、Step 4 から `build_liaison_html.py` を再実行。DevTools Console で Plotly CDN の読み込み失敗も確認。 |

**検算ルール（運用）**: meeting ごと `sum(weight_in) == LS in 行数`、split OFF 時 `sum(weight_out) == LS out の To をカンマ分割した総数`、split ON 時 `sum(weight_out) == LS out 行数`。実行時ログで確認できる。

---

## コーディング規約

- **Python/JS**: 1 行 100 文字目安（最大 120）。超えたら必ず改行する。
- **JS/CSS/HTML の生成**: `lines = [...]` → `"\n".join(lines)` 方式で組み立てる。1 行ベタ貼り禁止（viewer_template_builder.py は既にこの方式で実装済み）。
- **生成物は手編集禁止**。正は Python 側。viewer フォルダ配下は viewer_template_builder.py で再生成する。

---

## Notes

- 3GPP の FTP/Web 構造は会合により **TSGR_XX** / **TSGR_XXe** などが異なるため、固定 URL ではなく **Docs のディレクトリ一覧を取得し、該当 xlsx を正規表現で検出**する方式にしている。
- サーバ負荷に配慮し、DL スクリプトはリクエスト間にデフォルト 0.2 秒のスリープを入れている。必要に応じて `--sleep` で調整。
- オフライン検証: 手元に TDoc List の xlsx だけある場合、`files.txt` に 1 行 1 パスで列挙（相対パスは **list ファイルのディレクトリ**基準で解決）。その後 `build_liaison_excel` → `build_liaison_html` のみ実行して検証できる。
