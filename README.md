# NEWS アンナちゃん

マスコットキャラクター「アンナ・マリア・アブルッツィ」が毎朝ニュースダイジェストをDiscordに届けるシステムです。

## 特徴

- **マルチプロファイル**: トピックごとに別チャンネルへ投稿
- **無料運用**: GitHub Actions + Gemini API 無料枠で運用可能
- **カスタマイズ可能**: RSSソース・キーワード・プロファイルをYAMLで管理

## 構成

```
config/profiles.yml → 各プロファイルごとに:
  RSS feeds → Collector → Filter/Scorer → Gemini API → Formatter → Discord Webhook
```

### プロファイル一覧

| プロファイル | チャンネル | 内容 |
|-------------|-----------|------|
| IT業界 | `DISCORD_WEBHOOK_URL_IT` | AI、クラウド、セキュリティ等 |
| ゲーム（ユーザー向け） | `DISCORD_WEBHOOK_URL_GAME_USER` | 新作、セール、eスポーツ等 |
| ゲーム（開発者向け） | `DISCORD_WEBHOOK_URL_GAME_DEV` | エンジン、グラフィクス、GDC等 |

## セットアップ

### 1. GitHub Secrets の設定

リポジトリの Settings → Secrets and variables → Actions で以下を設定:

| Secret | 説明 |
|--------|------|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/apikey) で取得 |
| `DISCORD_WEBHOOK_URL_IT` | IT業界ニュース用チャンネルの Webhook URL |
| `DISCORD_WEBHOOK_URL_GAME_USER` | ゲームユーザー向けチャンネルの Webhook URL |
| `DISCORD_WEBHOOK_URL_GAME_DEV` | ゲーム開発者向けチャンネルの Webhook URL |

未設定の Webhook はスキップされます。必要なプロファイルだけ設定すれば OK です。

### 2. プロファイルの追加

新しいトピックを追加するには:

1. `config/<profile-name>/sources.yml` と `keywords.yml` を作成
2. `config/profiles.yml` にプロファイルを追加
3. `.github/workflows/daily_digest.yml` の env に Webhook シークレットを追加
4. GitHub Secrets に Webhook URL を登録

### 3. (任意) Gemini モデルの変更

Settings → Secrets and variables → Actions → Variables で `GEMINI_MODEL` を設定。
未設定時は `gemini-2.5-flash-lite` を使用。

## 実行方法

### GitHub Actions（自動）

毎朝 JST 07:30 に自動実行されます。

### GitHub Actions（手動テスト）

Actions タブ → Daily IT Digest → Run workflow → テストモードにチェック

### ローカル実行

```bash
pip install -r requirements.txt
export GEMINI_API_KEY="your-api-key"
export DISCORD_WEBHOOK_URL_IT="your-webhook-url"
python -m src.main
```

### Docker で実行

```bash
cp .env.example .env   # 値を設定
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
- Gemini API の無料枠には制限があります（30 RPM, 250K TPM）。プロファイル数 × 1回/日 の API 呼び出しが発生します
- RSS配信元の利用規約を尊重してください
- Gemini API が失敗した場合は、RSSの情報をもとに簡易ダイジェストが通知されます
