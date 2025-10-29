# コマンドライン使用ドキュメント

## 概要

AWS SSM Change Calendar 休業日スケジュール管理ツールのコマンドライン使用方法を詳しく説明します。

## 目次

1. [基本的な使用方法](#基本的な使用方法)
2. [グローバルオプション](#グローバルオプション)
3. [コマンド一覧](#コマンド一覧)
4. [使用例](#使用例)
5. [設定ファイル](#設定ファイル)
6. [環境変数](#環境変数)
7. [出力形式](#出力形式)

---

## 基本的な使用方法

### コマンド構文

```bash
python main.py [グローバルオプション] <コマンド> [コマンドオプション] [引数]
```

### ヘルプの表示

```bash
# 全体のヘルプ
python main.py --help

# 特定コマンドのヘルプ
python main.py <コマンド> --help
```

---

## グローバルオプション

すべてのコマンドで使用可能なオプションです。

### 基本オプション

| オプション | 短縮形 | 説明 | デフォルト |
|-----------|--------|------|-----------|
| `--config` | `-c` | 設定ファイルのパス | `~/.aws-ssm-calendar/config.json` |
| `--profile` | `-p` | AWSプロファイル名 | デフォルトプロファイル |
| `--region` | `-r` | AWSリージョン | `ap-northeast-1` |
| `--debug` | - | デバッグモードを有効化 | `False` |
| `--help` | - | ヘルプを表示 | - |

### ログ関連オプション

| オプション | 説明 | 選択肢 | デフォルト |
|-----------|------|--------|-----------|
| `--log-level` | ログレベル設定 | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | `INFO` |
| `--log-format` | ログ形式設定 | `simple`, `detailed`, `json`, `structured` | `structured` |
| `--no-monitoring` | パフォーマンス監視を無効化 | - | `False` |

### 使用例

```bash
# デバッグモードで実行
python main.py --debug holidays

# 特定のプロファイルとリージョンを使用
python main.py --profile production --region us-east-1 list-calendars

# JSON形式のログで実行
python main.py --log-format json --log-level DEBUG holidays
```

---

## コマンド一覧

### 1. 祝日関連コマンド

#### `holidays` - 祝日一覧表示・エクスポート

日本の祝日を表示またはICSファイルにエクスポートします。

```bash
python main.py holidays [オプション]
```

**オプション:**
- `--year`, `-y`: 表示する年（デフォルト: 現在年）
- `--output`, `-o`: ICSファイル出力パス
- `--exclude-sunday`: 日曜祝日を除外（デフォルト: 有効）
- `--format`: 出力形式（`table`, `json`, `csv`）

**使用例:**
```bash
# 今年の祝日を表示
python main.py holidays

# 2025年の祝日をICSファイルで出力
python main.py holidays --year 2025 --output holidays_2025.ics

# 日曜祝日を含めて出力
python main.py holidays --year 2024 --output holidays_all.ics --no-exclude-sunday

# JSON形式で出力
python main.py holidays --format json
```

#### `check-holiday` - 祝日判定

指定した日付が祝日かどうかを判定します。

```bash
python main.py check-holiday [オプション]
```

**オプション:**
- `--date`, `-d`: 判定する日付（YYYY-MM-DD形式、デフォルト: 今日）

**使用例:**
```bash
# 今日が祝日かチェック
python main.py check-holiday

# 特定の日付をチェック
python main.py check-holiday --date 2024-11-03

# 複数の日付をチェック
python main.py check-holiday --date 2024-01-01
python main.py check-holiday --date 2024-05-03
```

#### `refresh-holidays` - 祝日データ更新

祝日データを強制的に更新します。

```bash
python main.py refresh-holidays
```

**使用例:**
```bash
# 祝日データを最新に更新
python main.py refresh-holidays
```

### 2. AWS Change Calendar関連コマンド

#### `export` - Change Calendarエクスポート

AWS Change CalendarをICSファイルにエクスポートします。

```bash
python main.py export <calendar_name> [オプション]
```

**引数:**
- `calendar_name`: Change Calendar名

**オプション:**
- `--output`, `-o`: 出力ファイルパス
- `--timezone`, `-t`: タイムゾーン（デフォルト: UTC）
- `--include-holidays`: 日本の祝日を含める
- `--holidays-year`: 祝日の年（デフォルト: 現在年）

**使用例:**
```bash
# Change Calendarをエクスポート
python main.py export MyCalendar --output calendar.ics

# 祝日を含めてエクスポート
python main.py export MyCalendar --include-holidays --output calendar_with_holidays.ics

# 特定年の祝日を含める
python main.py export MyCalendar --include-holidays --holidays-year 2025 --output calendar_2025.ics
```

#### `list-calendars` - Change Calendar一覧

利用可能なChange Calendarを一覧表示します。

```bash
python main.py list-calendars
```

**使用例:**
```bash
# Change Calendar一覧を表示
python main.py list-calendars
```

#### `create-calendar` - Change Calendar作成

新しいChange Calendarを作成します。

```bash
python main.py create-calendar <calendar_name> [オプション]
```

**引数:**
- `calendar_name`: 作成するChange Calendar名

**オプション:**
- `--year`, `-y`: 祝日の年（デフォルト: 現在年）
- `--description`: カレンダーの説明
- `--exclude-sunday`: 日曜祝日を除外

**使用例:**
```bash
# 基本的なChange Calendar作成
python main.py create-calendar japanese-holidays-2024

# 説明付きで作成
python main.py create-calendar japanese-holidays-2024 --description "2024年日本祝日カレンダー"

# 日曜祝日を含めて作成
python main.py create-calendar japanese-holidays-2024 --no-exclude-sunday
```

#### `update-calendar` - Change Calendar更新

既存のChange Calendarを更新します。

```bash
python main.py update-calendar <calendar_name> [オプション]
```

**引数:**
- `calendar_name`: 更新するChange Calendar名

**オプション:**
- `--year`, `-y`: 祝日の年（デフォルト: 現在年）
- `--exclude-sunday`: 日曜祝日を除外

**使用例:**
```bash
# Change Calendarを更新
python main.py update-calendar japanese-holidays-2024

# 2025年の祝日で更新
python main.py update-calendar japanese-holidays-2024 --year 2025
```

#### `delete-calendar` - Change Calendar削除

Change Calendarを削除します。

```bash
python main.py delete-calendar <calendar_name>
```

**引数:**
- `calendar_name`: 削除するChange Calendar名

**使用例:**
```bash
# Change Calendarを削除（確認プロンプト付き）
python main.py delete-calendar old-calendar
```

### 3. ICS解析・比較コマンド

#### `analyze-ics` - ICSファイル解析

ICSファイルの内容を解析・表示します。

```bash
python main.py analyze-ics <ics_file> [オプション]
```

**引数:**
- `ics_file`: 解析するICSファイルのパス

**オプション:**
- `--format`: 出力形式（`human`, `json`, `csv`, `simple`）
- `--output`, `-o`: 結果をファイルに保存

**使用例:**
```bash
# ICSファイルを解析
python main.py analyze-ics holidays.ics

# JSON形式で出力
python main.py analyze-ics holidays.ics --format json

# 簡易形式で表示
python main.py analyze-ics holidays.ics --format simple

# 結果をファイルに保存
python main.py analyze-ics holidays.ics --output analysis.txt
```

#### `compare-ics` - ICSファイル比較

2つのICSファイルを比較します。

```bash
python main.py compare-ics <file1> <file2> [オプション]
```

**引数:**
- `file1`: 比較元ICSファイル
- `file2`: 比較先ICSファイル

**オプション:**
- `--format`: 比較形式（`standard`, `semantic`, `summary`）
- `--output`, `-o`: 結果をファイルに保存
- `--color`: カラー出力を有効化

**使用例:**
```bash
# 基本的な比較
python main.py compare-ics holidays_2024.ics holidays_2025.ics

# 意味的差分で比較
python main.py compare-ics holidays_old.ics holidays_new.ics --format semantic

# カラー出力で比較
python main.py compare-ics file1.ics file2.ics --color

# 結果をファイルに保存
python main.py compare-ics file1.ics file2.ics --output comparison.txt
```

#### `analyze-calendar` - AWS Change Calendar解析

AWS Change Calendarの内容を解析します。

```bash
python main.py analyze-calendar <calendar_name> [オプション]
```

**引数:**
- `calendar_name`: 解析するChange Calendar名

**オプション:**
- `--output`, `-o`: 結果をJSONファイルに保存
- `--format`: 出力形式（`human`, `json`, `summary`）

**使用例:**
```bash
# Change Calendarを解析
python main.py analyze-calendar japanese-holidays-2024

# JSON形式で保存
python main.py analyze-calendar japanese-holidays-2024 --output analysis.json

# サマリー形式で表示
python main.py analyze-calendar japanese-holidays-2024 --format summary
```

#### `compare-calendars` - 複数Change Calendar比較

複数のChange Calendarを比較します。

```bash
python main.py compare-calendars <calendar1> <calendar2> [calendar3...] [オプション]
```

**引数:**
- `calendar1`, `calendar2`, ...: 比較するChange Calendar名

**オプション:**
- `--output`, `-o`: 結果をJSONファイルに保存
- `--format`: 比較形式（`matrix`, `pairwise`, `summary`）

**使用例:**
```bash
# 2つのChange Calendarを比較
python main.py compare-calendars calendar-2024 calendar-2025

# 複数のカレンダーを一括比較
python main.py compare-calendars cal1 cal2 cal3 --format matrix

# 結果をファイルに保存
python main.py compare-calendars cal1 cal2 --output comparison.json
```

### 4. システム管理コマンド

#### `performance-metrics` - パフォーマンス監視

システムのパフォーマンス情報を表示します。

```bash
python main.py performance-metrics [オプション]
```

**オプション:**
- `--operation`: 特定の操作でフィルタ
- `--hours`: 時間範囲（時間単位、デフォルト: 1）

**使用例:**
```bash
# 過去1時間のメトリクス
python main.py performance-metrics

# 特定操作のメトリクス
python main.py performance-metrics --operation export_calendar

# 過去24時間のメトリクス
python main.py performance-metrics --hours 24
```

#### `system-metrics` - システム情報

システムの状態情報を表示します。

```bash
python main.py system-metrics
```

**使用例:**
```bash
# システム情報を表示
python main.py system-metrics
```

#### `enable-debug` / `disable-debug` - デバッグモード制御

デバッグモードの有効化・無効化を行います。

```bash
python main.py enable-debug
python main.py disable-debug
```

**使用例:**
```bash
# デバッグモードを有効化
python main.py enable-debug

# デバッグモードを無効化
python main.py disable-debug
```

---

## 使用例

### 基本的なワークフロー

#### 1. 初期セットアップ

```bash
# 祝日データの初期化
python main.py refresh-holidays

# AWS接続確認
python main.py list-calendars

# 今年の祝日確認
python main.py holidays
```

#### 2. Change Calendar作成

```bash
# 2024年の祝日カレンダーを作成
python main.py create-calendar japanese-holidays-2024 --year 2024

# 作成されたカレンダーを確認
python main.py analyze-calendar japanese-holidays-2024
```

#### 3. ICSファイル生成・比較

```bash
# 祝日ICSファイル生成
python main.py holidays --year 2024 --output holidays_2024.ics

# Change CalendarをICSでエクスポート
python main.py export japanese-holidays-2024 --output calendar_2024.ics

# 2つのファイルを比較
python main.py compare-ics holidays_2024.ics calendar_2024.ics
```

### 高度な使用例

#### バッチ処理

```bash
# 複数年のカレンダーを一括作成
for year in 2024 2025 2026; do
    python main.py create-calendar japanese-holidays-$year --year $year
done

# 複数年のICSファイルを生成
for year in 2024 2025 2026; do
    python main.py holidays --year $year --output holidays_$year.ics
done
```

#### 定期メンテナンス

```bash
#!/bin/bash
# 月次メンテナンススクリプト

# 祝日データ更新
python main.py refresh-holidays

# 今年と来年のカレンダー更新
current_year=$(date +%Y)
next_year=$((current_year + 1))

python main.py update-calendar japanese-holidays-$current_year --year $current_year
python main.py update-calendar japanese-holidays-$next_year --year $next_year

# システム状態確認
python main.py system-metrics
```

#### 比較・監査

```bash
# ローカルICSファイルとAWS Change Calendarの比較
python main.py holidays --year 2024 --output local_holidays.ics
python main.py export japanese-holidays-2024 --output aws_calendar.ics
python main.py compare-ics local_holidays.ics aws_calendar.ics --format semantic --color

# 複数のChange Calendarの一括比較
python main.py compare-calendars japanese-holidays-2024 japanese-holidays-2025 --format matrix
```

---

## 設定ファイル

### 設定ファイルの場所

デフォルトの設定ファイルパス:
- `~/.aws-ssm-calendar/config.json`
- `--config`オプションで別のパスを指定可能

### 設定ファイルの形式

```json
{
  "aws": {
    "region": "ap-northeast-1",
    "profile": null,
    "timeout": 30
  },
  "calendar": {
    "default_timezone": "Asia/Tokyo",
    "exclude_sunday_holidays": true,
    "output_format": "ics"
  },
  "output": {
    "directory": "./output",
    "filename_template": "{calendar_name}_{date}.ics",
    "encoding": "utf-8"
  },
  "cache": {
    "enabled": true,
    "ttl_days": 30,
    "directory": "~/.aws-ssm-calendar/cache",
    "max_size_mb": 100
  },
  "logging": {
    "level": "INFO",
    "format": "structured",
    "file": null,
    "enable_performance_monitoring": true
  }
}
```

### 設定項目の説明

| セクション | 項目 | 説明 | デフォルト |
|-----------|------|------|-----------|
| `aws` | `region` | AWSリージョン | `ap-northeast-1` |
| `aws` | `profile` | AWSプロファイル | `null` |
| `aws` | `timeout` | API タイムアウト（秒） | `30` |
| `calendar` | `default_timezone` | デフォルトタイムゾーン | `Asia/Tokyo` |
| `calendar` | `exclude_sunday_holidays` | 日曜祝日除外 | `true` |
| `output` | `directory` | 出力ディレクトリ | `./output` |
| `output` | `filename_template` | ファイル名テンプレート | `{calendar_name}_{date}.ics` |
| `cache` | `enabled` | キャッシュ有効化 | `true` |
| `cache` | `ttl_days` | キャッシュ有効期限（日） | `30` |

---

## 環境変数

### AWS関連

| 環境変数 | 説明 | 例 |
|---------|------|-----|
| `AWS_ACCESS_KEY_ID` | AWSアクセスキーID | `AKIAIOSFODNN7EXAMPLE` |
| `AWS_SECRET_ACCESS_KEY` | AWSシークレットアクセスキー | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |
| `AWS_SESSION_TOKEN` | AWSセッショントークン | `temporary-token` |
| `AWS_DEFAULT_REGION` | デフォルトリージョン | `ap-northeast-1` |
| `AWS_PROFILE` | 使用するプロファイル | `production` |

### アプリケーション関連

| 環境変数 | 説明 | 例 |
|---------|------|-----|
| `AWS_SSM_CALENDAR_CONFIG` | 設定ファイルパス | `/path/to/config.json` |
| `AWS_SSM_CALENDAR_CACHE_DIR` | キャッシュディレクトリ | `/tmp/cache` |
| `AWS_SSM_CALENDAR_LOG_LEVEL` | ログレベル | `DEBUG` |
| `AWS_SSM_CALENDAR_DEBUG` | デバッグモード | `true` |

### プロキシ関連

| 環境変数 | 説明 | 例 |
|---------|------|-----|
| `HTTP_PROXY` | HTTPプロキシ | `http://proxy.company.com:8080` |
| `HTTPS_PROXY` | HTTPSプロキシ | `http://proxy.company.com:8080` |
| `NO_PROXY` | プロキシ除外 | `localhost,127.0.0.1,.company.com` |

### 使用例

```bash
# 環境変数を設定してコマンド実行
export AWS_PROFILE=production
export AWS_DEFAULT_REGION=us-east-1
export AWS_SSM_CALENDAR_LOG_LEVEL=DEBUG

python main.py holidays --year 2024

# 一時的な環境変数設定
AWS_PROFILE=development python main.py list-calendars

# プロキシ環境での実行
HTTP_PROXY=http://proxy:8080 HTTPS_PROXY=http://proxy:8080 python main.py refresh-holidays
```

---

## 出力形式

### 標準出力形式

#### テーブル形式（デフォルト）

```
Japanese holidays for 2024:
┌────────────┬─────────────┬──────────────────┐
│ Date       │ Weekday     │ Holiday Name     │
├────────────┼─────────────┼──────────────────┤
│ 2024-01-01 │ Monday      │ 元日             │
│ 2024-01-08 │ Monday      │ 成人の日         │
│ 2024-02-11 │ Sunday      │ 建国記念の日     │
└────────────┴─────────────┴──────────────────┘

Statistics:
- Total holidays: 16
- Weekend holidays: 4
- Weekday holidays: 12
```

#### JSON形式

```json
{
  "holidays": [
    {
      "date": "2024-01-01",
      "name": "元日",
      "weekday": "Monday",
      "is_weekend": false
    }
  ],
  "statistics": {
    "total": 16,
    "weekend_holidays": 4,
    "weekday_holidays": 12
  }
}
```

#### CSV形式

```csv
Date,Weekday,Holiday Name,Is Weekend
2024-01-01,Monday,元日,false
2024-01-08,Monday,成人の日,false
2024-02-11,Sunday,建国記念の日,true
```

### ファイル出力

#### ICSファイル形式

```ics
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//AWS//Change Calendar 1.0//EN
X-CALENDAR-TYPE:DEFAULT_OPEN

BEGIN:VEVENT
UID:jp-holiday-20240101@aws-ssm-change-calendar
DTSTART;VALUE=DATE:20240101
DTEND;VALUE=DATE:20240102
SUMMARY:元日
DESCRIPTION:日本の国民の祝日
CATEGORIES:Japanese-Holiday
END:VEVENT

END:VCALENDAR
```

### エラー出力

#### 標準エラー形式

```
Error: AWS credentials not found
Suggestion: Run 'aws configure' to set up your credentials
Help: See docs/troubleshooting_and_faq.md for more information
```

#### デバッグ出力

```
[2024-01-01 12:00:00] DEBUG: Loading configuration from ~/.aws-ssm-calendar/config.json
[2024-01-01 12:00:01] DEBUG: Initializing AWS SSM client with region: ap-northeast-1
[2024-01-01 12:00:02] INFO: Fetching Japanese holidays for year 2024
[2024-01-01 12:00:03] DEBUG: Cache hit for holidays data
[2024-01-01 12:00:04] INFO: Found 16 holidays for 2024
```

---

このドキュメントを参考に、効率的にツールを活用してください。詳細な使用例やトラブルシューティングについては、`docs/usage_guide_and_best_practices.md`および`docs/troubleshooting_and_faq.md`を参照してください。