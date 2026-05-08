# Stock Check

yfinance から株価データを取得して、価格チャート・テクニカル指標（SMA / RSI / MACD / Bollinger）を可視化する Streamlit アプリ。

⚠️ 教育・試作目的。投資判断は本人の責任で行ってください。

## 機能

- 銘柄コード入力で価格履歴・時価総額・PER を取得
- 移動平均（SMA20/50）+ ボリンジャーバンド付き価格チャート
- RSI(14) / MACD タブ
- 直近60本の生データテーブル

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
| `app.py` | Streamlit UI |
| `stock_data.py` | yfinance 取得レイヤー + 複数銘柄 CLI |
| `indicators.py` | SMA / RSI / MACD / Bollinger |
| `ai_advisor.py` | Claude API 投資判断（ローカル専用） |
| `fetch_stock.py` | 単一銘柄 CLI |
