# 要件定義書

## 概要

AWS SSM Change Calendar 休業日スケジュール管理ツールは、日本の祝日を効率的に管理し、AWS Systems Manager Change Calendarに休業日として設定するための包括的なツールです。

**主要機能:**

1. **祝日データ取得**: 内閣府公式HPからCSV形式の祝日データを一次ソースとして取得
2. **データ加工**: 文字エンコーディングをUTF-8に変換し、当年以降のデータのみを抽出
3. **ICS変換**: AWS SSM Change Calendar仕様に準拠したiCalendar 2.0 (ICS)形式への変換
4. **ICS解析**: 生成されたICSファイルを人間が理解しやすい形式で表示・検証
5. **ICS比較**: 異なるバージョンのICSファイル間の差分を時系列でソート・表示

**対象システム:**
- AWS Systems Manager Change Calendar（主要対象）
- 標準的なカレンダーアプリケーション（Google Calendar、Outlook、Apple Calendar等）

**データソース:**
- 内閣府公式祝日CSV（https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv）

## 用語集

- **AWS SSM**: Amazon Web Services Systems Manager
- **Change Calendar**: AWS SSMの機能で、システム変更やメンテナンスの許可・禁止期間を管理
- **休業日スケジュール**: システムメンテナンスや変更作業を禁止する日程（祝日、休日等）
- **Japanese Holidays**: 内閣府が定義する日本の国民の祝日・休日
- **ICS**: カレンダーデータ交換用のiCalendarフォーマット（RFC 5545）
- **ICS解析**: ICSファイルの内容を構造化して人間が理解しやすい形式で表示する機能
- **ICS比較**: 複数のICSファイル間の差分を検出・表示する機能
- **一次ソース**: 内閣府公式HPなど、データの原典となる信頼できる情報源
- **当年以降フィルタ**: 現在年から将来の祝日データのみを抽出する処理
- **CLI**: コマンドラインインターフェース
- **UTC**: 協定世界時
- **Cache**: 頻繁にアクセスされるデータのローカルストレージ
- **UTF-8変換**: 文字エンコーディングをUTF-8形式に統一する処理

## 要件

### 要件1 - 日本祝日データ取得・管理

**ユーザーストーリー:** システム管理者として、日本の祝日データを効率的に取得・管理したい。これにより、Change Calendarの休業日情報が常に最新で正確であることを保証できる。

#### 受入基準

1. **一次ソースからの取得**: システムが内閣府公式CSV（https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv）から祝日データを直接取得する
2. **文字エンコーディング変換**: 取得したCSVファイルをUTF-8形式に自動変換し、文字化けを防止する
3. **当年以降フィルタリング**: 現在の日時を取得し、当年以降の祝日データのみを抽出・利用する
4. **キャッシュ管理**: 処理済み祝日データを`~/.aws-ssm-calendar/cache/japanese_holidays.csv`にUTF-8形式で保存し、30日間の有効期限を設定する
5. **データインテグリティ**: 公式データの取得に失敗した場合、システムは処理を停止し、明確なエラーメッセージを表示する

#### 詳細仕様

**データ取得プロセス:**
```
1. 内閣府HPからCSVファイルをダウンロード
2. 文字エンコーディングを自動検出（Shift_JIS/CP932 → UTF-8変換）
3. 現在日時を取得し、当年以降の祝日データを抽出
4. UTF-8形式でローカルキャッシュに保存
5. 処理対象データとして利用
```

**エンコーディング処理:**
- **検出順序**: Shift_JIS → CP932 → UTF-8
- **変換処理**: 検出されたエンコーディングからUTF-8への変換
- **エラー処理**: 変換失敗時は元のエンコーディングで再試行
- **検証**: 変換後データの妥当性確認（日本語文字の正常表示）

**当年以降フィルタリング:**
- **基準日**: システム実行時の現在日付
- **対象範囲**: 基準日の年から将来の全祝日
- **例**: 2024年10月実行時 → 2024年1月1日以降の全祝日を対象
- **年度管理**: 年が変わった際の自動更新対応

**日本祝日決定プロセス:**
- 内閣府は毎年2月頃に翌年の祝日を正式決定・公表する
- 春分の日・秋分の日は天文計算により前年に決定される
- 振替休日・国民の休日は祝日法に基づき自動決定される

**データ取得フロー:**
```
起動 → キャッシュ確認 → 有効期限チェック → 必要時ダウンロード → エンコーディング検出 → CSV解析 → 当年以降フィルタ → キャッシュ保存
```

**エラーハンドリング:**
- HTTPタイムアウト: 30秒
- ネットワーク障害: 処理停止、キャッシュ利用可能時のみ継続
- 解析エラー: 該当行スキップして継続、重大エラー時は処理停止
- データ整合性チェック: 取得データの妥当性検証（日付形式、祝日名の存在確認）

**データインテグリティ要件:**
- 公式データのみ使用: 内閣府CSV以外のデータソースは使用しない
- データ検証: 取得した祝日データの形式・内容を厳密に検証
- 処理継続条件: 有効なキャッシュが存在する場合のみネットワーク障害時に継続
- エラー時動作: 不完全なデータでの処理実行を禁止

**パフォーマンス要件:**
- 初回ダウンロード: 3秒以内
- キャッシュ読み込み: 50ms以内
- メモリ使用量: 100KB以内（当年以降のみ保持）

### 要件2 - AWS SSM Change Calendar用ICS変換

**ユーザーストーリー:** 運用チームとして、日本の祝日データをAWS SSM Change Calendar用のiCalendar 2.0 (ICS)形式でエクスポートしたい。これにより、AWS SSM Change Calendarに祝日を休業日として設定でき、祝日期間中のシステム変更を自動的に防止できる。

#### 受入基準

1. **AWS SSM仕様準拠**: システムはAWS SSM Change Calendar専用のICS形式（PRODID: -//AWS//Change Calendar 1.0//EN）を生成する
2. **当年以降データ変換**: 取得・加工された当年以降の祝日データをICS形式に変換する
3. **文字エンコーディング**: ICSファイルをUTF-8エンコーディングで生成し、日本語祝日名を正しく表示する
4. **イベントプロパティ**: 各祝日イベントに必須プロパティ（UID、DTSTAMP、SUMMARY、DTSTART、DTEND）を含める
5. **AWS SSM互換性**: 生成されたICSファイルがAWS SSM Change Calendarで正常にインポート・認識される
6. **日曜祝日フィルタリング**: システムは日曜日に該当する祝日を除外するオプションを提供する（デフォルト：除外）

#### 詳細仕様

**AWS SSM Change Calendar専用ICS構造:**
```
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//AWS//Change Calendar 1.0//EN
X-CALENDAR-TYPE:DEFAULT_OPEN
X-WR-CALDESC:
X-CALENDAR-CMEVENTS:DISABLED
X-WR-TIMEZONE:Asia/Tokyo

BEGIN:VTIMEZONE
TZID:Asia/Tokyo
BEGIN:STANDARD
DTSTART:19700101T000000
TZOFFSETTFROM:+0900
TZOFFSETTO:+0900
TZNAME:JST
END:STANDARD
END:VTIMEZONE

BEGIN:VEVENT
UID:jp-holiday-YYYYMMDD@aws-ssm-change-calendar
DTSTAMP:20241029T120000Z
DTSTART;TZID=Asia/Tokyo:YYYYMMDDTHHMISS
DTEND;TZID=Asia/Tokyo:YYYYMMDDTHHMISS
SUMMARY:日本の祝日: 祝日名
DESCRIPTION:日本の国民の祝日: 祝日名
CATEGORIES:Japanese-Holiday
END:VEVENT

END:VCALENDAR
```

**変換処理フロー:**
```
当年以降祝日データ → ICSイベント生成 → AWS SSM形式適用 → UTF-8エンコーディング → ファイル出力
```

### 要件3 - ICSファイル解析・可視化

**ユーザーストーリー:** カレンダー管理者として、生成されたICSファイルの内容を人間が理解しやすい形式で確認したい。これにより、カレンダーデータの正確性を検証し、問題があれば迅速に対応できる。

#### 受入基準

1. **ICS解析機能**: システムがICSファイルを読み込み、イベント情報を構造化されたデータとして解析する
2. **人間可読形式出力**: 解析されたカレンダーデータを日付順にソートし、表形式で表示する
3. **統計情報表示**: 総イベント数、対象期間、祝日の種類別集計を表示する
4. **エラー検出**: ICSファイル内の構文エラーや不正なデータを検出・報告する
5. **複数形式対応**: 標準出力、JSON、CSV形式での出力をサポートする
6. **簡易出力形式**: サマリー情報とイベントリストを含む簡潔な出力形式を提供する

#### 詳細仕様

**解析対象プロパティ:**
- DTSTART/DTEND: イベントの開始・終了日時
- SUMMARY: イベントのタイトル（祝日名）
- DESCRIPTION: イベントの詳細説明
- UID: イベントの一意識別子
- CATEGORIES: イベントのカテゴリ分類

**出力形式例:**
```
=== カレンダー解析結果 ===
対象期間: 2025年1月1日 - 2025年12月31日
総イベント数: 16件

日付        祝日名           カテゴリ      UID
2025-01-01  元日            Japanese-Holiday  jp-holiday-20250101@aws-ssm-change-calendar
2025-01-13  成人の日        Japanese-Holiday  jp-holiday-20250113@aws-ssm-change-calendar
...

=== 統計情報 ===
- 国民の祝日: 16件
- 振替休日: 0件
- 国民の休日: 0件
```

**エラー検出項目:**
- 必須プロパティの欠落
- 日付形式の不正
- 重複するUID
- 不正な文字エンコーディング
- RFC 5545違反

### 要件4 - CLIユーザビリティとデフォルト設定

**ユーザーストーリー:** 一般ユーザーとして、CLIツールを使用する際にクリーンで読みやすい出力を得たい。また、必要に応じて詳細な情報やデバッグ情報を有効化できるようにしたい。これにより、日常的な使用では簡潔な情報を、トラブルシューティング時には詳細な情報を得ることができる。

#### 受入基準

1. **デフォルトクリーン出力**: システムはデフォルトでクリーンで読みやすい出力を提供し、不要な技術的詳細を非表示にする
2. **段階的詳細化**: ユーザーはオプション指定により、必要に応じて詳細レベルを段階的に上げることができる
3. **ログレベル制御**: システムはデフォルトでWARNINGレベル以上のメッセージのみを表示し、INFOやDEBUGレベルは明示的な指定時のみ表示する
4. **モニタリング制御**: システムはデフォルトでパフォーマンス監視やシステムメトリクスを非表示にし、明示的な指定時のみ表示する
5. **出力フォーマット制御**: システムはデフォルトでシンプルなテキスト形式を使用し、構造化ログは明示的な指定時のみ使用する
6. **後方互換性**: 既存の詳細出力が必要なユーザーは適切なオプション指定により従来と同等の出力を得ることができる

#### 詳細仕様

**デフォルト設定:**
- **ログレベル**: `WARNING`（警告以上のメッセージのみ表示）
- **ログフォーマット**: `simple`（シンプルなテキスト形式）
- **システムモニタリング**: `無効`（パフォーマンス情報を非表示）

**段階的詳細化オプション:**
```bash
# レベル1: 通常使用（デフォルト）
python main.py holidays

# レベル2: 詳細情報付き
python main.py --log-level INFO holidays

# レベル3: モニタリング付き
python main.py --log-level INFO --enable-monitoring holidays

# レベル4: 開発者向け（最大詳細）
python main.py --debug --log-level DEBUG --log-format structured --enable-monitoring holidays
```

**出力例比較:**

*デフォルト出力（レベル1）:*
```
Japanese holidays for 2025:
  2025-01-01 (Wed) - 元日
  2025-01-13 (Mon) - 成人の日
  ...
```

*詳細出力（レベル4）:*
```json
{
  "timestamp": "2025-10-30T03:05:45.954925",
  "level": "INFO",
  "logger": "src.logging_config",
  "message": "System monitoring started (interval: 60.0s)",
  ...
}
Japanese holidays for 2025:
  2025-01-01 (Wed) - 元日
  2025-01-13 (Mon) - 成人の日
  ...
{
  "timestamp": "2025-10-30T03:05:46.960467",
  "level": "INFO",
  "message": "System metrics - CPU: 25.9%, Memory: 55.9%",
  ...
}
```

**CLI オプション仕様:**
- `--log-level [DEBUG|INFO|WARNING|ERROR|CRITICAL]`: ログレベル設定（デフォルト: WARNING）
- `--log-format [simple|detailed|json|structured]`: ログフォーマット設定（デフォルト: simple）
- `--enable-monitoring`: パフォーマンス・システム監視有効化（デフォルト: 無効）
- `--debug`: デバッグモード有効化（ログレベルをDEBUGに設定）

**移行ガイド:**
- v1.0.x以前の詳細出力が必要な場合: `--log-level INFO --enable-monitoring` を追加
- 開発・デバッグ時: `--debug --log-format structured --enable-monitoring` を使用

### 要件5 - ICSファイル比較・差分表示

**ユーザーストーリー:** システム管理者として、異なるバージョンのICSファイル間の差分を確認したい。これにより、カレンダーの更新内容を把握し、変更の妥当性を検証できる。

#### 受入基準

1. **ファイル比較機能**: 2つのICSファイルを読み込み、イベントレベルでの差分を検出する
2. **時系列ソート**: 比較結果を日付順にソートして表示する
3. **変更種別表示**: 追加・削除・変更されたイベントを明確に区別して表示する
4. **詳細差分表示**: 変更されたイベントの具体的な変更内容（プロパティレベル）を表示する
5. **サマリー情報**: 変更の概要統計（追加X件、削除Y件、変更Z件）を表示する

#### 詳細仕様

**比較アルゴリズム:**
- 主キー: UID（イベント一意識別子）による照合
- 副キー: DTSTART（開始日時）による照合（UID不一致時）
- プロパティ比較: SUMMARY、DTSTART、DTEND、DESCRIPTION等の差分検出

**出力形式例:**
```
=== ICSファイル比較結果 ===
ファイル1: japanese-holidays-2024.ics (16イベント)
ファイル2: japanese-holidays-2025.ics (16イベント)

=== 変更サマリー ===
追加: 16件
削除: 16件
変更: 0件

=== 詳細差分 ===
[削除] 2024-01-01 元日 (jp-holiday-20240101@aws-ssm-change-calendar)
[削除] 2024-01-08 成人の日 (jp-holiday-20240108@aws-ssm-change-calendar)
...
[追加] 2025-01-01 元日 (jp-holiday-20250101@aws-ssm-change-calendar)
[追加] 2025-01-13 成人の日 (jp-holiday-20250113@aws-ssm-change-calendar)
...
```

**比較対象プロパティ:**
- DTSTART: 開始日時の変更
- DTEND: 終了日時の変更
- SUMMARY: 祝日名の変更
- DESCRIPTION: 説明文の変更
- CATEGORIES: カテゴリの変更

**エラーハンドリング:**
- ファイル読み込みエラー: 詳細なエラーメッセージを表示
- 形式不正: 比較可能な部分のみ処理継続
- メモリ不足: 大容量ファイル処理時の適切な警告

#### 4.2 イベント意味的Diff形式比較表示（拡張要件）

**User Story:** As a システム管理者, I want ICSファイルのイベント内容の差分をdiff形式で表示したい, so that 同じイベントの有無や期間の違いを直感的に把握し、カレンダー変更の影響を正確に理解できる

#### Acceptance Criteria

1. WHEN 2つのICSファイルを比較する時, THE ICS_Comparator SHALL イベント単位での意味的diff形式表示を提供する

2. THE ICS_Comparator SHALL 以下のイベント比較ロジックを使用する:
   - 主キー照合: UID（イベント一意識別子）による同一イベント判定
   - 副キー照合: DTSTART + SUMMARY による類似イベント判定
   - プロパティ比較: 日時、タイトル、説明の変更検出

3. WHILE イベントdiff表示を行う時, THE ICS_Comparator SHALL 以下の記号を使用する:
   - "+" 記号: 追加されたイベント
   - "-" 記号: 削除されたイベント
   - "~" 記号: 変更されたイベント（変更前後を表示）
   - "=" 記号: 移動されたイベント（日時変更）

4. WHERE イベントプロパティが変更された場合, THE ICS_Comparator SHALL 変更内容を以下の形式で表示する:
   ```
   ~ [変更] 2025-02-23 天皇誕生日
     - 開始時刻: 2025-02-23 09:00 → 2025-02-23 00:00
     - 説明: "国民の祝日" → "国民の祝日（日曜日）"
   ```

5. THE ICS_Comparator SHALL イベントを日付順にソートして差分表示する

6. WHEN 同一イベントの期間が変更された場合, THE ICS_Comparator SHALL 期間変更として明確に表示する

7. THE ICS_Comparator SHALL イベント差分統計を表示する:
   - 追加イベント数、削除イベント数、変更イベント数
   - 期間変更イベント数、移動イベント数

8. THE ICS_Comparator SHALL diff形式出力をファイルに保存する機能を提供する

9. WHERE 変更がない場合, THE ICS_Comparator SHALL "イベントに差分はありません"メッセージを表示する

10. THE ICS_Comparator SHALL カラー出力オプション（緑=追加、赤=削除、黄=変更、青=移動）を提供する

**期待される出力例:**
```diff
=== ICSイベント意味的差分 ===
ファイル1: japanese_holidays_2025.ics (37イベント)
ファイル2: japanese_holidays_2025_exclude_sunday.ics (33イベント)

=== 変更統計 ===
+ 追加: 0 イベント
- 削除: 4 イベント  
~ 変更: 0 イベント
= 移動: 0 イベント

=== 詳細差分（日付順） ===

- [削除] 2025-02-23 天皇誕生日
  UID: jp-holiday-20250223@aws-ssm-change-calendar
  期間: 2025-02-23 00:00 - 2025-02-24 00:00
  説明: 国民の祝日（日曜日）

- [削除] 2025-05-04 みどりの日  
  UID: jp-holiday-20250504@aws-ssm-change-calendar
  期間: 2025-05-04 00:00 - 2025-05-05 00:00
  説明: 国民の祝日（日曜日）

- [削除] 2025-11-23 勤労感謝の日
  UID: jp-holiday-20251123@aws-ssm-change-calendar
  期間: 2025-11-23 00:00 - 2025-11-24 00:00
  説明: 国民の祝日（日曜日）

- [削除] 2026-05-03 憲法記念日
  UID: jp-holiday-20260503@aws-ssm-change-calendar
  期間: 2026-05-03 00:00 - 2026-05-04 00:00
  説明: 国民の祝日（日曜日）
```

**技術仕様:**
- **Event Matching Algorithm**: UID主キー + DTSTART/SUMMARY副キー照合
- **Property Comparison**: DTSTART、DTEND、SUMMARY、DESCRIPTION、CATEGORIES
- **Output Format**: 構造化diff形式（人間可読）
- **Sorting**: 日付順（DTSTART基準）
- **Color Support**: ANSI カラーコード対応
- **File Encoding**: UTF-8対応
- **Statistics**: 変更種別ごとの統計情報

**イベント変更検出ロジック:**
- **追加**: ファイル2にのみ存在するUID
- **削除**: ファイル1にのみ存在するUID  
- **変更**: 同一UIDで異なるプロパティ値
- **移動**: 同一UIDで異なるDTSTART/DTEND
- **期間変更**: 同一UIDで異なる期間長

**パフォーマンス要件:**
- **処理時間**: 1000イベント以下のファイルで3秒以内
- **メモリ使用量**: イベント数に比例した効率的使用
- **大容量対応**: 10MB以上のICSファイルでの適切な処理

#### 4.3 AWS Change Calendar統合比較（拡張要件）

**User Story:** As a システム管理者, I want 生成したICSファイルと既存のAWS Change Calendarの内容を比較したい, so that 実際のAWS環境との差分を把握し、デプロイ前の検証や既存カレンダーとの整合性を確認できる

#### Acceptance Criteria

1. THE ICS_Comparator SHALL AWS SSM Change Calendarから既存のカレンダー内容を取得する機能を提供する

2. WHEN AWS Change Calendarと比較する時, THE ICS_Comparator SHALL AWS APIを使用してカレンダードキュメントを取得する

3. THE ICS_Comparator SHALL 取得したAWS Change Calendarの内容をICS形式に正規化して比較する

4. WHERE AWS認証が必要な場合, THE ICS_Comparator SHALL AWS SDK認証チェーンを使用する

5. THE ICS_Comparator SHALL AWS Change CalendarとローカルICSファイルの意味的diff比較を提供する

6. WHEN AWS Change Calendarが存在しない場合, THE ICS_Comparator SHALL 適切なエラーメッセージを表示する

7. THE ICS_Comparator SHALL AWS Change Calendarの状態（OPEN/CLOSED）情報も比較結果に含める

8. THE ICS_Comparator SHALL 複数のAWS Change Calendarとの一括比較機能を提供する

9. THE ICS_Comparator SHALL AWS Change Calendar比較結果を専用フォーマットで出力する

10. THE ICS_Comparator SHALL AWS Change Calendar比較時のエラーハンドリング（権限不足、ネットワークエラー等）を適切に処理する

**期待される出力例:**
```diff
=== AWS Change Calendar比較結果 ===
ローカルファイル: japanese_holidays_2025.ics (37イベント)
AWS Change Calendar: japanese-holidays-2025 (33イベント, 状態: OPEN)
リージョン: us-east-1

=== 変更統計 ===
+ ローカルのみ: 4 イベント
- AWSのみ: 0 イベント  
~ 差異: 0 イベント
= 移動: 0 イベント

=== 詳細差分（日付順） ===

+ [ローカルのみ] 2025-02-23 天皇誕生日
  UID: jp-holiday-20250223@aws-ssm-change-calendar
  期間: 2025-02-23 00:00 - 2025-02-24 00:00
  説明: 国民の祝日（日曜日）
  → AWS Change Calendarに追加推奨

+ [ローカルのみ] 2025-05-04 みどりの日
  UID: jp-holiday-20250504@aws-ssm-change-calendar
  期間: 2025-05-04 00:00 - 2025-05-05 00:00
  説明: 国民の祝日（日曜日）
  → AWS Change Calendarに追加推奨

=== 推奨アクション ===
1. 4件のローカルイベントをAWS Change Calendarに追加
2. AWS Change Calendarの更新後、状態確認を実施
3. 次回比較: 2025-11-01（推奨）
```

**技術仕様:**
- **AWS Integration**: boto3 SSM クライアント使用
- **Authentication**: AWS SDK認証チェーン（プロファイル、環境変数、IAMロール）
- **API Operations**: GetDocument, ListDocuments, GetCalendarState
- **Data Normalization**: AWS Change Calendar → ICS形式変換
- **Error Handling**: AWSエラー、ネットワークエラー、権限エラーの適切な処理
- **Output Format**: AWS専用比較結果フォーマット

**必要なAWS権限:**
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ssm:GetDocument",
                "ssm:ListDocuments",
                "ssm:GetCalendarState"
            ],
            "Resource": "*"
        }
    ]
}
```

**パフォーマンス要件:**
- **AWS API呼び出し**: 5秒以内でのレスポンス
- **大容量カレンダー**: 1000イベント以上での適切な処理
- **ネットワーク最適化**: 必要最小限のAPI呼び出し

