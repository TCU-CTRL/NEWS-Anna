# IT Morning Digest

IT業界の最新ニュースを毎朝自動で収集し、Gemini APIで日本語要約を生成してDiscordへ通知するシステムです。

## 特徴

- **無料運用**: GitHub Actions + Gemini API無料枠で運用可能
- **サーバレス**: データベースや外部サーバ不要
- **カスタマイズ可能**: RSSソースやキーワードをYAMLで管理

## 構成

```
RSS feeds → Collector → Filter/Scorer → Gemini API → Formatter → Discord Webhook
```

## セットアップ

### 1. GitHub Secrets の設定

リポジトリの Settings → Secrets and variables → Actions で以下を設定:

| Secret | 説明 |
|--------|------|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/apikey) で取得 |
| `DISCORD_WEBHOOK_URL` | Discordチャンネル設定 → 連携サービス → ウェブフック → 新しいウェブフック |

### 2. (任意) Gemini モデルの変更

Settings → Secrets and variables → Actions → Variables で `GEMINI_MODEL` を設定。
未設定時は `gemini-2.5-flash-lite` を使用。

### 3. RSSソースの追加・変更

`config/sources.yml` を編集:

```yaml
sources:
  - name: "新しいソース"
    url: "https://example.com/feed.xml"
    category: "your_category"
    enabled: true
    weight: 1.0
```

### 4. キーワードの変更

`config/keywords.yml` を編集して、優先度別のキーワードを調整。

## 実行方法

### GitHub Actions（自動）

毎朝 JST 07:30 に自動実行されます。

### GitHub Actions（手動）

Actions タブ → Daily IT Digest → Run workflow

### ローカル実行

```bash
pip install -r requirements.txt
export GEMINI_API_KEY="your-api-key"
export DISCORD_WEBHOOK_URL_IT="your-webhook-url"
python -m src.main
```

### Docker で実行

```bash
# .env を作成（.env.example をコピーして値を設定）
cp .env.example .env

# 実行
docker compose up --build

# テスト
docker compose run --rm digest pytest tests/ -v
```

## テスト

```bash
pip install -r requirements.txt
pytest tests/ -v
```

## 注意事項

- データの永続保存は行いません。同じ記事が翌日も通知される可能性があります
- Gemini API の無料枠には制限があります（30 RPM, 250K TPM）。1日1回の実行であれば問題ありません
- RSS配信元の利用規約を尊重してください
- Gemini API が失敗した場合は、RSSの情報をもとに簡易ダイジェストが通知されます
