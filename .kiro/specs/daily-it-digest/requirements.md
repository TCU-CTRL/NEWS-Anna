# Requirements Document

## Introduction
IT業界の最新動向を毎朝自動で収集し、AIによる日本語要約を生成してチャットサービスへ通知するシステム。無料運用を最優先とし、外部サーバやデータベースを使わずに、CI/CDプラットフォーム上のスケジュール実行で完結する。データの永続保存は行わず、各実行は独立した単発処理として動作する。

## Boundary Context
- **In scope**: RSSフィード収集、記事フィルタリング・スコアリング、AI要約生成、チャット通知、YAML設定管理、ログ出力、単体テスト
- **Out of scope**: 記事の永続保存、既読管理（実行をまたぐ重複排除）、記事本文の全文取得・スクレイピング、Webダッシュボード・UI、ユーザー認証、複数チャンネルへの通知振り分け
- **Adjacent expectations**: CI/CDプラットフォームがcronスケジュール実行と手動実行を提供すること。AI要約APIが外部サービスとして利用可能であること。チャット通知先がWebhookエンドポイントを提供すること。

## Requirements

### Requirement 1: スケジュール実行
**Objective:** As a IT業界の動向を追うエンジニア, I want 毎朝決まった時刻にニュースダイジェストを受け取りたい, so that 業務開始前に重要な動向を把握できる

#### Acceptance Criteria
1. The Daily Digest shall 毎日 JST 07:30（UTC 22:30）にスケジュール実行される
2. The Daily Digest shall 手動トリガーによる任意のタイミングでの実行をサポートする
3. When スケジュール実行または手動実行がトリガーされた場合, the Daily Digest shall RSS収集から通知完了までの全パイプラインを自動で実行する

### Requirement 2: RSSフィード収集
**Objective:** As a IT業界の動向を追うエンジニア, I want 複数のRSSフィードから記事を自動収集したい, so that 国内外の幅広いIT情報源をカバーできる

#### Acceptance Criteria
1. The Daily Digest shall YAML設定ファイルに定義されたRSSフィードの一覧を読み込む
2. When 設定ファイルにRSSソースが定義されている場合, the Daily Digest shall 各ソースからRSS/Atomフィードを取得する
3. The Daily Digest shall 各ソースに対して名前、URL、カテゴリ、有効/無効フラグ、重みの設定を保持する
4. When RSSソースの有効フラグが無効に設定されている場合, the Daily Digest shall そのソースからの取得をスキップする
5. If 特定のRSSソースの取得に失敗した場合, the Daily Digest shall 失敗したソース名をログに記録し、他のソースの処理を継続する

### Requirement 3: 記事フィルタリング
**Objective:** As a IT業界の動向を追うエンジニア, I want 不要な記事が除外され重要な記事だけが選別されたい, so that ノイズの少ない質の高いダイジェストを受け取れる

#### Acceptance Criteria
1. The Daily Digest shall タイトルまたはURLが空の記事を除外する
2. The Daily Digest shall 同一実行内でURLが重複する記事を1件にまとめる
3. The Daily Digest shall 直近24〜48時間以内に公開された記事を優先する
4. When 記事の公開日時が取得できない場合, the Daily Digest shall その記事を除外せず低スコアとして扱う
5. The Daily Digest shall AI要約に渡す記事数を最大10件に制限する
6. The Daily Digest shall 最終的に通知する記事数を最大5件に制限する

### Requirement 4: キーワードスコアリング
**Objective:** As a IT業界の動向を追うエンジニア, I want 自分の関心分野に合わせて記事の優先順位が付けられたい, so that 最も関連性の高いニュースが上位に表示される

#### Acceptance Criteria
1. The Daily Digest shall YAML設定ファイルで優先度別（高・中・低）のキーワードリストを管理する
2. When 記事のタイトルまたはサマリーに高優先度キーワードが含まれる場合, the Daily Digest shall そのキーワード一致に対してスコアを加算する
3. When 記事のタイトルまたはサマリーに中優先度キーワードが含まれる場合, the Daily Digest shall 高優先度より低いスコアを加算する
4. When 記事のタイトルまたはサマリーに低優先度キーワードが含まれる場合, the Daily Digest shall 中優先度より低いスコアを加算する
5. The Daily Digest shall ソースの重み設定をスコア計算に反映する
6. The Daily Digest shall 新しい記事ほどスコアが高くなるよう時間減衰を適用する

### Requirement 5: AI要約生成
**Objective:** As a IT業界の動向を追うエンジニア, I want 収集された記事がAIで日本語要約されたい, so that 短時間で要点を把握できる

#### Acceptance Criteria
1. The Daily Digest shall スコア上位の記事（最大10件）をまとめて1回のAPI呼び出しで要約する
2. The Daily Digest shall 記事のタイトル、サマリー、URL、ソース名、カテゴリのみをAI APIに渡す（本文全文は渡さない）
3. The Daily Digest shall AI要約の出力に、各記事のタイトル、カテゴリ、重要度、要約（3行以内）、重要な理由、原文URLを含む
4. The Daily Digest shall AI要約の出力に、日付入りのヘッダー、総評、追うべきキーワードを含む
5. The Daily Digest shall AIモデルを環境変数で指定可能とし、未指定時はデフォルトモデルを使用する
6. The Daily Digest shall APIキーを環境変数から読み込む（コードへの直書き禁止）

### Requirement 6: フォールバック処理
**Objective:** As a IT業界の動向を追うエンジニア, I want AI要約が失敗してもニュース情報を受け取りたい, so that APIの障害時でも最低限の情報を得られる

#### Acceptance Criteria
1. If AI要約APIの呼び出しが失敗した場合, the Daily Digest shall スコア上位5件の記事のタイトル・サマリー・URLをそのまま通知する
2. If AI要約APIの呼び出しが失敗した場合, the Daily Digest shall 通知の冒頭にAI要約が失敗した旨のメッセージを付加する
3. If AI要約APIの呼び出しが失敗した場合, the Daily Digest shall システム全体を異常終了させない

### Requirement 7: チャット通知
**Objective:** As a IT業界の動向を追うエンジニア, I want ダイジェストがチャットサービスに自動通知されたい, so that 普段使うコミュニケーションツールで情報を確認できる

#### Acceptance Criteria
1. The Daily Digest shall Webhook URLを環境変数から読み込む（コードへの直書き禁止）
2. The Daily Digest shall 通知メッセージをMarkdown形式で読みやすくフォーマットする
3. When 通知メッセージが2000文字を超える場合, the Daily Digest shall メッセージを複数に分割して送信する
4. When 通知が正常に送信された場合, the Daily Digest shall 成功をログに記録する
5. If 通知の送信に失敗した場合, the Daily Digest shall 失敗をログに記録する

### Requirement 8: 設定管理
**Objective:** As a システム管理者, I want RSSソースやキーワードをコード変更なしに編集したい, so that 情報源や関心分野を柔軟に調整できる

#### Acceptance Criteria
1. The Daily Digest shall RSSソース一覧をYAML設定ファイルで管理する
2. The Daily Digest shall キーワード優先度一覧をYAML設定ファイルで管理する
3. The Daily Digest shall 環境変数の例を記載したテンプレートファイルを提供する

### Requirement 9: ログ出力
**Objective:** As a システム管理者, I want 実行状況をログで確認したい, so that 問題発生時に原因を特定できる

#### Acceptance Criteria
1. The Daily Digest shall 読み込んだRSSソース数をログに出力する
2. The Daily Digest shall 取得した記事数をログに出力する
3. The Daily Digest shall フィルタリング後の記事数をログに出力する
4. The Daily Digest shall AI APIに渡した記事数をログに出力する
5. The Daily Digest shall 通知の成功または失敗をログに出力する
6. The Daily Digest shall RSS取得に失敗したソース名をログに出力する

### Requirement 10: テスト
**Objective:** As a 開発者, I want 主要なロジックに対する自動テストがあること, so that 変更時に既存機能の破壊を検知できる

#### Acceptance Criteria
1. The Daily Digest shall URL重複排除ロジックの単体テストを備える
2. The Daily Digest shall キーワードスコアリングロジックの単体テストを備える
3. The Daily Digest shall メッセージ文字数分割ロジックの単体テストを備える
