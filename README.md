# Stock Check

yfinance から株価データを取得して、価格チャート・テクニカル指標（SMA / RSI / MACD / Bollinger）を可視化する Streamlit アプリ。

⚠️ 教育・試作目的。投資判断は本人の責任で行ってください。

## 機能

ホーム（詳細）画面に加え、サイドバーから5機能に切り替え可能。

- **詳細** (`app.py`) — 銘柄個別の価格チャート + SMA/RSI/MACD/Bollinger
- **ウォッチリスト** — 保存した複数銘柄の現在値・騰落率一覧。URL に保存（ブックマーク・共有可）
- **銘柄比較** — 始点を 100 に揃えた相対パフォーマンス比較チャート
- **配当履歴** — 年次配当の棒グラフ + 全支払履歴 + 配当利回り
- **ニュース** — yfinance 経由の最新ニュース記事一覧
- **企業情報** — 52週レンジ、PER/PBR/Beta/ROE 等のファンダメンタル + 事業概要

## ローカル起動

```bash
pip install -r requirements.txt
python -m streamlit run app.py
```

## デプロイ（Streamlit Community Cloud）

1. このリポジトリを GitHub に push
2. https://share.streamlit.io にサインイン → "New app"
3. リポジトリ・ブランチ・`app.py` を選択 → "Deploy"

## オプション: AI 投資判断ドラフト（自分用）

`ai_advisor.py` は Claude Opus 4.7 で投資判断のドラフトを生成します。公開デプロイでは無効化されています（API コストが発生するため）。

ローカルで使う場合:

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
$env:ENABLE_AI = "1"
python -m streamlit run app.py
```

CLI から直接:

```powershell
python ai_advisor.py 7203.T
```

## ファイル構成

| ファイル | 役割 |
|---|---|
| `app.py` | エントリ + 詳細画面 |
| `pages/1_Watchlist.py` | ウォッチリスト |
| `pages/2_Compare.py` | 銘柄比較 |
| `pages/3_Dividends.py` | 配当履歴 |
| `pages/4_News.py` | ニュース |
| `pages/5_Company.py` | 企業情報 |
| `_lib.py` | ページ共通（キャッシュ + ウォッチリスト永続化） |
| `stock_data.py` | yfinance 取得レイヤー + 複数銘柄 CLI |
| `indicators.py` | SMA / RSI / MACD / Bollinger |
| `ai_advisor.py` | Claude API 投資判断（ローカル専用） |
| `fetch_stock.py` | 単一銘柄 CLI |
