# Implementation Plan

- [x] 1. Foundation: プロジェクト基盤セットアップ

- [x] 1.1 プロジェクトスキャフォールディング
  - `requirements.txt` を作成し、必要最小限の依存パッケージを定義する（feedparser, PyYAML, requests, google-genai, python-dateutil, pytest）
  - `.env.example` を作成し、環境変数テンプレートを定義する（GEMINI_API_KEY, GEMINI_MODEL, DISCORD_WEBHOOK_URL）
  - `src/__init__.py` を空ファイルとして作成し、パッケージ構造を確立する
  - `pip install -r requirements.txt` が正常に完了すること
  - _Requirements: 8.3_

- [x] 1.2 データモデルと設定型定義
  - `src/models.py` に Article dataclass を定義する（title, url, source, category, published_at, summary, score）
  - `src/config_loader.py` に SourceConfig dataclass（name, url, category, enabled, weight）と KeywordConfig dataclass（high_priority, medium_priority, low_priority）を定義する
  - `load_sources()` 関数を実装し、YAML ファイルから `list[SourceConfig]` を返す
  - `load_keywords()` 関数を実装し、YAML ファイルから `KeywordConfig` を返す
  - Python インタープリタで `from src.models import Article` と `from src.config_loader import load_sources, load_keywords` がインポートできること
  - _Requirements: 2.1, 2.3, 4.1, 8.1, 8.2_
  - _Boundary: models, ConfigLoader_

- [x] 1.3 YAML設定ファイル作成
  - `config/sources.yml` を作成し、初期RSSソース5件（ITmedia NEWS, Zenn, Qiita, Hacker News, AWS News Blog）を定義する（URLはプレースホルダ）
  - `config/keywords.yml` を作成し、高・中・低優先度キーワードリストを定義する
  - `load_sources()` と `load_keywords()` で正しくパースできること
  - _Requirements: 2.1, 4.1, 8.1, 8.2_
  - _Boundary: ConfigLoader_

- [x] 2. Core: パイプラインコンポーネント実装

- [x] 2.1 (P) RSSフィード収集（Collector）
  - `src/collector.py` に `collect_articles(sources: list[SourceConfig]) -> list[Article]` を実装する
  - feedparser で各ソースの RSS/Atom フィードを取得し、Article リストに変換する
  - `published_parsed` から datetime への変換を行い、取得できない場合は None を設定する
  - 有効フラグが False のソースをスキップする
  - 個別ソースの取得失敗時は例外を投げず、ログに失敗ソース名を記録し処理を続行する
  - 読み込んだRSSソース数、取得した記事数をログ出力する
  - 有効なRSSフィードURLを1件設定し、`collect_articles()` 呼び出しで Article リストが返ること
  - _Requirements: 2.2, 2.4, 2.5, 9.1, 9.2, 9.6_
  - _Boundary: Collector_

- [x] 2.2 (P) フィルタリング・スコアリング（Filter）
  - `src/filter.py` に以下の関数を実装する:
    - `deduplicate(articles) -> list[Article]`: URL重複排除
    - `remove_invalid(articles) -> list[Article]`: タイトル空・URL空の記事除外
    - `score_articles(articles, keywords) -> list[Article]`: キーワードスコアリング
    - `select_top(articles, limit=10) -> list[Article]`: スコア降順で上位選出
  - スコアリングロジック: 高優先度 +3.0、中優先度 +2.0、低優先度 +0.5、ソースweight乗算、時間減衰（24h以内 +2.0、48h以内 +1.0）
  - published_at が None の記事は時間ボーナスなし（+0.0）で低スコアとして処理
  - フィルタ後の記事数をログ出力する
  - テスト用の Article リストを渡して、重複排除・スコア計算・上位選出が正しく動作すること
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.2, 4.3, 4.4, 4.5, 4.6, 9.3_
  - _Boundary: Filter_

- [x] 2.3 (P) Gemini API 要約生成（Summarizer）
  - `src/summarizer_gemini.py` に `summarize(articles: list[Article]) -> str | None` を実装する
  - `GEMINI_API_KEY` 環境変数から API キーを読み込む
  - `GEMINI_MODEL` 環境変数からモデル名を読み込み、未設定時は `gemini-2.5-flash-lite` を使用する
  - `google.genai.Client` で最大10件の記事（title, summary, url, source, category）を1回のAPI呼び出しで要約する
  - プロンプトに日本語ダイジェスト形式（ヘッダー、総評、最大5件の重要ニュース、追うべきキーワード）を指定する
  - API呼び出し失敗時は例外を捕捉し、エラーログを出力して None を返す（システム全体を異常終了させない）
  - Geminiに渡した記事数をログ出力する
  - `GEMINI_API_KEY` 設定済みの環境で `summarize()` を呼び出し、ダイジェストテキストが返ること（または API 未設定時に None が返ること）
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 6.3, 9.4_
  - _Boundary: Summarizer_

- [x] 2.4 (P) メッセージ整形・分割（Formatter）
  - `src/formatter.py` に以下の関数を実装する:
    - `format_digest(digest_text: str) -> list[str]`: AI要約テキストをDiscord向けに整形・分割
    - `format_fallback(articles: list[Article]) -> list[str]`: フォールバック用の簡易ダイジェスト生成
    - `split_messages(text: str, limit: int = 2000) -> list[str]`: テキストを指定文字数で分割
  - フォールバックメッセージの冒頭に「⚠ Gemini APIによる要約に失敗したため、RSS情報をもとに簡易ダイジェストを送信します。」を付加する
  - 分割後の各メッセージが2000文字以下であること
  - 2000文字を超えるテキストを `split_messages()` に渡して、全チャンクが2000文字以下で返ること
  - _Requirements: 6.1, 6.2, 7.2, 7.3_
  - _Boundary: Formatter_

- [x] 2.5 (P) Discord Webhook 通知（Notifier）
  - `src/notifier.py` に `send_to_discord(messages: list[str]) -> bool` を実装する
  - `DISCORD_WEBHOOK_URL` 環境変数から Webhook URL を読み込む
  - 各メッセージを `{"content": message}` として requests.post で送信する
  - 送信成功時にログ出力する
  - 送信失敗時にエラーログを出力し、False を返す（例外で異常終了させない）
  - `DISCORD_WEBHOOK_URL` 設定済みの環境で `send_to_discord(["test"])` を呼び出し、200系レスポンスが返ること
  - _Requirements: 7.1, 7.3, 7.4, 7.5, 9.5_
  - _Boundary: Notifier_

- [x] 3. Integration: パイプライン統合

- [x] 3.1 オーケストレーター実装
  - `src/main.py` にパイプライン全体の実行フローを実装する
  - 実行順序: 設定読み込み → RSS収集 → フィルタ・スコアリング → AI要約 → フォーマット → 通知
  - AI要約（Summarizer）が None を返した場合、Formatter のフォールバック関数で簡易ダイジェストを生成する分岐を実装する
  - 最終通知する記事数を最大5件に制限する（AI要約プロンプトで制御 + フォールバック時は select_top で5件選出）
  - `python -m src.main` でエラーなく実行が完了すること（環境変数設定済みの場合）
  - _Requirements: 1.3, 3.6, 6.1, 6.2, 6.3_
  - _Depends: 2.1, 2.2, 2.3, 2.4, 2.5_
  - _Boundary: main_

- [x] 3.2 GitHub Actions ワークフロー定義
  - `.github/workflows/daily_digest.yml` を作成する
  - cron スケジュール `30 22 * * *`（JST 07:30）を設定する
  - `workflow_dispatch` による手動実行を有効にする
  - Ubuntu latest、Python 3.11 環境でセットアップする
  - Secrets から `GEMINI_API_KEY`、`DISCORD_WEBHOOK_URL` を環境変数に設定する
  - `GEMINI_MODEL` は vars または env で任意設定可能にする
  - `pip install -r requirements.txt && python -m src.main` を実行する
  - YAML 構文が正しく、GitHub Actions のバリデーションを通過すること
  - _Requirements: 1.1, 1.2, 1.3_
  - _Depends: 3.1_
  - _Boundary: GitHub Actions_

- [x] 4. Validation: 単体テスト

- [x] 4.1 (P) URL重複排除テスト
  - `tests/test_filter.py` に URL 重複排除のテストケースを実装する
  - 同一URLの記事が1件にまとまることを検証する
  - URLが異なる記事がすべて保持されることを検証する
  - タイトル空・URL空の記事が除外されることを検証する
  - `pytest tests/test_filter.py` が全テストパスすること
  - _Requirements: 10.1_
  - _Boundary: Filter_

- [x] 4.2 (P) キーワードスコアリングテスト
  - `tests/test_ranker.py` にスコアリングのテストケースを実装する
  - 高優先度キーワード一致で +3.0 が加算されることを検証する
  - 中優先度キーワード一致で +2.0 が加算されることを検証する
  - 低優先度キーワード一致で +0.5 が加算されることを検証する
  - ソース weight がスコアに反映されることを検証する
  - 時間減衰（24h以内 +2.0、48h以内 +1.0、それ以外 +0.0）が適用されることを検証する
  - `pytest tests/test_ranker.py` が全テストパスすること
  - _Requirements: 10.2_
  - _Boundary: Filter_

- [x] 4.3 (P) メッセージ分割テスト
  - `tests/test_formatter.py` にメッセージ分割のテストケースを実装する
  - 2000文字以内のテキストが分割されないことを検証する
  - 2000文字を超えるテキストが正しく複数チャンクに分割されることを検証する
  - 分割後の各チャンクが2000文字以下であることを検証する
  - フォールバックメッセージの冒頭にエラーメッセージが含まれることを検証する
  - `pytest tests/test_formatter.py` が全テストパスすること
  - _Requirements: 10.3_
  - _Boundary: Formatter_
