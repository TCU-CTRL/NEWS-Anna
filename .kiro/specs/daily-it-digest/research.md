# Research & Design Decisions

## Summary
- **Feature**: `daily-it-digest`
- **Discovery Scope**: New Feature（グリーンフィールド、成熟技術のため Light Discovery）
- **Key Findings**:
  - パイプラインアーキテクチャが最適（各ステージ独立、Article リストで接続）
  - 全主要ライブラリが成熟・安定しており、互換性リスクは低い
  - Gemini API の無料枠制限を考慮し、1回のAPI呼び出しで最大10件を処理する設計

## Research Log

### Gemini API SDK (google-genai)
- **Context**: AI要約生成のSDK選定
- **Findings**:
  - google-genai ~1.74.0+ (Apache 2.0)
  - 旧 `google-generativeai` は非推奨、`google-genai` を使用
  - `genai.Client(api_key=...)` → `client.models.generate_content(model=..., contents=...)` のパターン
  - モデル名: `gemini-2.5-flash-lite`（NOT preview）
  - Thinking がデフォルトで有効（トークン消費に注意）
  - 無料枠: 30 RPM, 250K TPM（プロジェクト単位で適用）
- **Implications**: SDK のインターフェースに合わせて Summarizer を実装。1日1回のバッチ呼び出しなら無料枠は十分。

### Discord Webhook API
- **Context**: 通知先の API 仕様確認
- **Findings**:
  - POST `{"content": "message", "username": "bot"}` でテキスト送信
  - 1メッセージ2000文字制限（content フィールド）
  - Markdown サブセット対応（content/embeds 内のみ、username/title/footer は非対応）
  - レート制限: 30 requests/minute per webhook URL
- **Implications**: Formatter でメッセージ分割ロジックが必要

### RSS/Atom フィード解析
- **Context**: feedparser の機能確認
- **Findings**:
  - feedparser 6.0.12 (BSD-2-Clause)
  - RSS 0.9x, RSS 1.0, RSS 2.0, Atom 0.3/1.0 に対応
  - `published_parsed` で日付取得可能（UTC 9-tuple）、フィードによっては欠損
  - python-dateutil 3.9.0 で RFC 822 等の柔軟な日付パースが可能
- **Implications**: published_at が None のケースを考慮したスコアリング設計

### その他ライブラリ
- **requests** 2.33.1 (Apache 2.0): `json=` パラメータで自動 Content-Type 設定
- **PyYAML** 6.0.3 (MIT): `yaml.safe_load()` を使用（`yaml.load()` は禁止）

## Design Decisions

### Decision: パイプラインアーキテクチャ
- **Context**: 複数のデータ変換ステージを持つバッチ処理システム
- **Alternatives Considered**:
  1. パイプライン（直列処理）— 各ステージが関数として独立
  2. イベント駆動 — メッセージキューで各ステージを接続
- **Selected Approach**: パイプライン（直列処理）
- **Rationale**: 単一プロセスで完結するバッチ処理であり、イベント駆動の複雑さは不要。テスト容易性も高い。
- **Trade-offs**: 並列処理による高速化は得られないが、処理対象が少量（最大数十件）のため問題なし

### Decision: フォールバック戦略
- **Context**: AI API が失敗した場合の対応
- **Selected Approach**: RSS 情報からの簡易ダイジェスト生成
- **Rationale**: 無料枠の制限やAPI障害時でも最低限の価値を提供する。追加コストなし。

## Risks & Mitigations
- Gemini API 無料枠超過 → 1日1回、1回のAPI呼び出しに制限する設計で対応
- RSSフィード配信元の変更・停止 → YAML設定で容易にソース追加・変更可能
- Discord Webhook URL の漏洩 → 環境変数/Secrets で管理、コードに直書きしない
