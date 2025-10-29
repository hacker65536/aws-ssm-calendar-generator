# ユーザーマニュアル

## 概要

AWS SSM Change Calendar 休業日スケジュール管理ツールの包括的なユーザーマニュアルです。このドキュメントは、初心者から上級者まで、すべてのユーザーが効率的にツールを活用できるよう設計されています。

## 目次

1. [はじめに](#はじめに)
2. [インストールガイド](#インストールガイド)
3. [基本的な使用方法](#基本的な使用方法)
4. [高度な機能](#高度な機能)
5. [運用ガイド](#運用ガイド)
6. [トラブルシューティング](#トラブルシューティング)
7. [リファレンス](#リファレンス)

---

## はじめに

### このツールについて

AWS SSM Change Calendar 休業日スケジュール管理ツールは、日本の祝日を効率的に管理し、AWS Systems Manager Change Calendarに統合するためのコマンドラインツールです。

### 主な機能

- **祝日データ管理**: 内閣府公式データから日本の祝日を自動取得
- **AWS統合**: Change Calendarの作成・更新・削除・比較
- **ICS生成**: RFC 5545準拠のiCalendarファイル生成
- **解析・比較**: ICSファイルやChange Calendarの詳細分析
- **自動化**: バッチ処理やCI/CD統合のサポート

### 対象ユーザー

- **システム管理者**: AWS環境での運用自動化
- **DevOpsエンジニア**: CI/CDパイプラインでの祝日考慮
- **開発者**: アプリケーションでの祝日判定機能
- **運用担当者**: 定期的なカレンダーメンテナンス

---

## インストールガイド

### クイックインストール

最も簡単なインストール方法：

```bash
# 1. リポジトリのクローン
git clone https://github.com/your-org/aws-ssm-calendar-generator.git
cd aws-ssm-calendar-generator

# 2. 仮想環境の作成と有効化
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# または .venv\Scripts\activate  # Windows

# 3. 依存関係のインストール
pip install -r requirements.txt

# 4. AWS認証設定
aws configure

# 5. 動作確認
python main.py holidays
```

### 詳細なインストール手順

システム要件、トラブルシューティングを含む詳細な手順については、[インストールとセットアップガイド](installation_and_setup_guide.md)を参照してください。

---

## 基本的な使用方法

### 1. 初期セットアップ

#### 祝日データの初期化

```bash
# 祝日データを内閣府から取得
python main.py refresh-holidays
```

#### AWS接続確認

```bash
# AWS認証と接続を確認
python main.py list-calendars
```

### 2. 祝日の確認と管理

#### 祝日一覧の表示

```bash
# 今年の祝日を表示
python main.py holidays

# 特定年の祝日を表示
python main.py holidays --year 2025

# JSON形式で出力
python main.py holidays --format json
```

#### 特定日の祝日判定

```bash
# 今日が祝日かチェック
python main.py check-holiday

# 特定日をチェック
python main.py check-holiday --date 2024-11-03

# 結果例
2024-11-03 (Sunday) は祝日です: 文化の日
```

#### 祝日データの更新

```bash
# 手動でデータを更新
python main.py refresh-holidays

# 更新後の確認
python main.py holidays --year 2024
```

### 3. ICSファイルの生成

#### 基本的なICS生成

```bash
# 今年の祝日をICSファイルで出力
python main.py holidays --output holidays_2024.ics

# 特定年のICSファイル生成
python main.py holidays --year 2025 --output holidays_2025.ics
```

#### 日曜祝日の扱い

```bash
# 日曜祝日を除外（デフォルト）
python main.py holidays --output holidays_exclude_sunday.ics

# 日曜祝日を含める
python main.py holidays --no-exclude-sunday --output holidays_include_sunday.ics
```

### 4. AWS Change Calendarの操作

#### Change Calendarの作成

```bash
# 基本的な作成
python main.py create-calendar japanese-holidays-2024 --year 2024

# 説明付きで作成
python main.py create-calendar japanese-holidays-2024 \
  --year 2024 \
  --description "2024年日本祝日カレンダー"
```

#### Change Calendarの更新

```bash
# 既存カレンダーを更新
python main.py update-calendar japanese-holidays-2024 --year 2025
```

#### Change Calendarのエクスポート

```bash
# Change CalendarをICSファイルにエクスポート
python main.py export japanese-holidays-2024 --output exported_calendar.ics

# 祝日を含めてエクスポート
python main.py export japanese-holidays-2024 \
  --include-holidays \
  --output calendar_with_holidays.ics
```

### 5. 解析と比較

#### ICSファイルの解析

```bash
# ICSファイルの内容を解析
python main.py analyze-ics holidays.ics

# 簡易形式で表示
python main.py analyze-ics holidays.ics --format simple

# JSON形式で保存
python main.py analyze-ics holidays.ics --format json --output analysis.json
```

#### ファイル比較

```bash
# 2つのICSファイルを比較
python main.py compare-ics holidays_2024.ics holidays_2025.ics

# 意味的差分で比較
python main.py compare-ics file1.ics file2.ics --format semantic

# カラー出力で比較
python main.py compare-ics file1.ics file2.ics --color
```

---

## 高度な機能

### 1. バッチ処理

#### 複数年のカレンダー生成

```bash
#!/bin/bash
# 複数年のカレンダーを一括生成

for year in 2024 2025 2026; do
    echo "生成中: $year年"
    python main.py holidays --year $year --output "holidays_$year.ics"
    python main.py create-calendar "japanese-holidays-$year" --year $year
done

echo "完了: 3年分のカレンダーを生成しました"
```

#### 定期メンテナンススクリプト

```bash
#!/bin/bash
# monthly_maintenance.sh - 月次メンテナンス

# 祝日データ更新
python main.py refresh-holidays

# 今年と来年のカレンダー更新
current_year=$(date +%Y)
next_year=$((current_year + 1))

python main.py update-calendar "japanese-holidays-$current_year" --year $current_year
python main.py update-calendar "japanese-holidays-$next_year" --year $next_year

# システム状態確認
python main.py system-metrics

echo "月次メンテナンス完了: $(date)"
```

### 2. 設定ファイルの活用

#### 高度な設定例

```json
{
  "aws": {
    "region": "ap-northeast-1",
    "profile": "production",
    "timeout": 30
  },
  "calendar": {
    "default_timezone": "Asia/Tokyo",
    "exclude_sunday_holidays": true,
    "output_format": "ics"
  },
  "output": {
    "directory": "./output",
    "filename_template": "{calendar_name}_{year}_{date}.ics",
    "encoding": "utf-8"
  },
  "cache": {
    "enabled": true,
    "ttl_days": 30,
    "directory": "~/.aws-ssm-calendar/cache",
    "max_size_mb": 100,
    "compression": true
  },
  "logging": {
    "level": "INFO",
    "format": "structured",
    "file": "~/.aws-ssm-calendar/logs/application.log",
    "enable_performance_monitoring": true
  },
  "performance": {
    "memory_optimization": true,
    "concurrent_processing": {
      "max_workers": 4
    }
  }
}
```

#### 環境別設定

```bash
# 開発環境
python main.py --config config-dev.json holidays

# 本番環境
python main.py --config config-prod.json create-calendar prod-holidays-2024

# テスト環境
python main.py --config config-test.json --debug holidays
```

### 3. CI/CD統合

#### GitHub Actions統合例

```yaml
# .github/workflows/holiday-calendar-sync.yml
name: Holiday Calendar Sync

on:
  schedule:
    - cron: '0 2 1 * *'  # 毎月1日の午前2時
  workflow_dispatch:

jobs:
  sync-calendars:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: pip install -r requirements.txt
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ap-northeast-1
    
    - name: Update holiday calendars
      run: |
        python main.py refresh-holidays
        current_year=$(date +%Y)
        next_year=$((current_year + 1))
        
        python main.py update-calendar japanese-holidays-$current_year --year $current_year
        python main.py update-calendar japanese-holidays-$next_year --year $next_year
    
    - name: Generate reports
      run: |
        python main.py analyze-calendar japanese-holidays-$(date +%Y) --output calendar-analysis.json
    
    - name: Upload artifacts
      uses: actions/upload-artifact@v3
      with:
        name: calendar-reports
        path: |
          *.json
          *.ics
```

#### Terraform統合例

```hcl
# terraform/change_calendar.tf
locals {
  current_year = formatdate("YYYY", timestamp())
  next_year    = tostring(tonumber(local.current_year) + 1)
}

# 祝日ICSファイル生成
resource "null_resource" "generate_holiday_calendar" {
  for_each = toset([local.current_year, local.next_year])
  
  triggers = {
    year = each.value
  }
  
  provisioner "local-exec" {
    command = "python ../main.py holidays --year ${each.value} --output ../output/holidays_${each.value}.ics"
  }
}

# Change Calendar作成
resource "aws_ssm_document" "japanese_holidays" {
  for_each = toset([local.current_year, local.next_year])
  
  name            = "japanese-holidays-${each.value}"
  document_type   = "ChangeCalendar"
  document_format = "TEXT"
  
  content = file("../output/holidays_${each.value}.ics")
  
  tags = {
    Environment = var.environment
    Purpose     = "Japanese Holidays"
    Year        = each.value
    ManagedBy   = "Terraform"
  }
  
  depends_on = [null_resource.generate_holiday_calendar]
}
```

### 4. 監視とアラート

#### パフォーマンス監視

```bash
# パフォーマンスメトリクスの確認
python main.py performance-metrics

# 特定操作のメトリクス
python main.py performance-metrics --operation export_calendar --hours 24

# システム情報の確認
python main.py system-metrics
```

#### ログ監視スクリプト

```bash
#!/bin/bash
# log_monitor.sh - ログ監視とアラート

LOG_FILE="$HOME/.aws-ssm-calendar/logs/application.log"
ERROR_THRESHOLD=5
WARNING_THRESHOLD=10

# エラー数をカウント
error_count=$(grep -c "ERROR" "$LOG_FILE" 2>/dev/null || echo 0)
warning_count=$(grep -c "WARNING" "$LOG_FILE" 2>/dev/null || echo 0)

# アラート判定
if [ "$error_count" -gt "$ERROR_THRESHOLD" ]; then
    echo "ALERT: エラーが閾値を超えました ($error_count > $ERROR_THRESHOLD)"
    # Slack通知やメール送信などの処理
    curl -X POST -H 'Content-type: application/json' \
        --data "{\"text\":\"AWS SSM Calendar Tool: エラー数が閾値を超えました ($error_count)\"}" \
        "$SLACK_WEBHOOK_URL"
fi

if [ "$warning_count" -gt "$WARNING_THRESHOLD" ]; then
    echo "WARNING: 警告が閾値を超えました ($warning_count > $WARNING_THRESHOLD)"
fi

# 最新のエラーを表示
if [ "$error_count" -gt 0 ]; then
    echo "最新のエラー:"
    grep "ERROR" "$LOG_FILE" | tail -3
fi
```

---

## 運用ガイド

### 1. 定期メンテナンス

#### 推奨メンテナンススケジュール

| 頻度 | タスク | コマンド例 |
|------|--------|-----------|
| **毎日** | システム状態確認 | `python main.py system-metrics` |
| **週次** | ログローテーション | `find ~/.aws-ssm-calendar/logs -name "*.log" -mtime +7 -delete` |
| **月次** | 祝日データ更新 | `python main.py refresh-holidays` |
| **月次** | Change Calendar更新 | `python main.py update-calendar japanese-holidays-$(date +%Y)` |
| **年次** | 翌年カレンダー作成 | `python main.py create-calendar japanese-holidays-$(($(date +%Y) + 1))` |

#### cron設定例

```bash
# crontab -e で以下を追加

# 毎日午前2時にシステム状態確認
0 2 * * * /path/to/venv/bin/python /path/to/main.py system-metrics >> /var/log/ssm-calendar-daily.log 2>&1

# 毎月1日午前3時に祝日データ更新
0 3 1 * * /path/to/venv/bin/python /path/to/main.py refresh-holidays >> /var/log/ssm-calendar-monthly.log 2>&1

# 毎月1日午前4時にChange Calendar更新
0 4 1 * * /path/to/scripts/monthly_maintenance.sh >> /var/log/ssm-calendar-maintenance.log 2>&1
```

### 2. バックアップとリストア

#### 設定とデータのバックアップ

```bash
#!/bin/bash
# backup.sh - 設定とデータのバックアップ

BACKUP_DIR="/backup/aws-ssm-calendar/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# 設定ファイルのバックアップ
cp -r ~/.aws-ssm-calendar/config.json "$BACKUP_DIR/"

# キャッシュデータのバックアップ
cp -r ~/.aws-ssm-calendar/cache/ "$BACKUP_DIR/"

# 生成されたICSファイルのバックアップ
cp -r ./output/ "$BACKUP_DIR/"

# AWS Change Calendarのバックアップ（エクスポート）
for calendar in $(python main.py list-calendars --format json | jq -r '.[].name'); do
    python main.py export "$calendar" --output "$BACKUP_DIR/${calendar}.ics"
done

echo "バックアップ完了: $BACKUP_DIR"
```

#### リストア手順

```bash
#!/bin/bash
# restore.sh - バックアップからのリストア

BACKUP_DIR="$1"

if [ -z "$BACKUP_DIR" ]; then
    echo "使用方法: $0 <backup_directory>"
    exit 1
fi

# 設定ファイルのリストア
cp "$BACKUP_DIR/config.json" ~/.aws-ssm-calendar/

# キャッシュデータのリストア
cp -r "$BACKUP_DIR/cache/" ~/.aws-ssm-calendar/

# ICSファイルのリストア
cp -r "$BACKUP_DIR/output/" ./

echo "リストア完了: $BACKUP_DIR"
```

### 3. セキュリティ管理

#### 認証情報の管理

```bash
# AWS認証情報の定期ローテーション
# 1. 新しいアクセスキーを作成
aws iam create-access-key --user-name ssm-calendar-user

# 2. 新しい認証情報でテスト
AWS_ACCESS_KEY_ID=new-key AWS_SECRET_ACCESS_KEY=new-secret python main.py list-calendars

# 3. 設定を更新
aws configure set aws_access_key_id new-key
aws configure set aws_secret_access_key new-secret

# 4. 古いアクセスキーを削除
aws iam delete-access-key --user-name ssm-calendar-user --access-key-id old-key
```

#### ファイル権限の管理

```bash
# セキュアな権限設定
chmod 700 ~/.aws-ssm-calendar/
chmod 600 ~/.aws-ssm-calendar/config.json
chmod 600 ~/.aws/credentials
chmod 755 ./output/

# 定期的な権限チェック
find ~/.aws-ssm-calendar -type f -not -perm 600 -ls
find ~/.aws-ssm-calendar -type d -not -perm 700 -ls
```

### 4. 災害復旧

#### 災害復旧計画

1. **データ損失時の復旧手順**
   ```bash
   # 1. 祝日データの再取得
   python main.py refresh-holidays
   
   # 2. 設定ファイルの復元
   cp /backup/config.json ~/.aws-ssm-calendar/
   
   # 3. Change Calendarの再作成
   python main.py create-calendar japanese-holidays-$(date +%Y) --year $(date +%Y)
   ```

2. **AWS環境の復旧**
   ```bash
   # Terraformでの一括復旧
   cd terraform/
   terraform plan
   terraform apply
   ```

3. **動作確認**
   ```bash
   # 基本機能の確認
   python main.py holidays
   python main.py list-calendars
   python main.py system-metrics
   ```

---

## トラブルシューティング

### クイック診断

問題が発生した場合、まず以下のクイック診断を実行してください：

```bash
#!/bin/bash
# 1分間診断スクリプト

echo "=== クイック診断 ==="

# Python環境
python --version && echo "✓ Python OK" || echo "✗ Python NG"

# 依存パッケージ
python -c "import boto3, icalendar, click" && echo "✓ パッケージ OK" || echo "✗ パッケージ NG"

# AWS認証
aws sts get-caller-identity >/dev/null 2>&1 && echo "✓ AWS認証 OK" || echo "✗ AWS認証 NG"

# ネットワーク
curl -s -I https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv | grep -q "200" && echo "✓ ネットワーク OK" || echo "✗ ネットワーク NG"

# 基本機能
python main.py --help >/dev/null 2>&1 && echo "✓ 基本機能 OK" || echo "✗ 基本機能 NG"

echo "=== 診断完了 ==="
```

### よくある問題と解決方法

詳細なトラブルシューティングについては、[トラブルシューティングとFAQ](troubleshooting_and_faq.md)を参照してください。

#### 緊急時の対処

1. **サービス停止時**
   ```bash
   # キャッシュデータで継続
   python main.py holidays  # キャッシュから読み込み
   ```

2. **AWS接続エラー時**
   ```bash
   # ローカルICSファイルで代替
   python main.py holidays --output emergency_holidays.ics
   ```

3. **データ破損時**
   ```bash
   # 強制的にデータを再取得
   rm -rf ~/.aws-ssm-calendar/cache/*
   python main.py refresh-holidays
   ```

---

## リファレンス

### コマンドリファレンス

全コマンドの詳細については、[コマンドライン使用ドキュメント](command_line_reference.md)を参照してください。

### API リファレンス

プログラマー向けのAPI仕様については、[API リファレンス](comprehensive_api_reference.md)を参照してください。

### 設定リファレンス

#### 設定ファイルの完全な例

```json
{
  "aws": {
    "region": "ap-northeast-1",
    "profile": null,
    "timeout": 30,
    "retry_count": 3,
    "retry_delay": 1
  },
  "calendar": {
    "default_timezone": "Asia/Tokyo",
    "exclude_sunday_holidays": true,
    "output_format": "ics",
    "date_format": "%Y-%m-%d"
  },
  "output": {
    "directory": "./output",
    "filename_template": "{calendar_name}_{year}_{date}.ics",
    "encoding": "utf-8",
    "line_ending": "CRLF"
  },
  "cache": {
    "enabled": true,
    "ttl_days": 30,
    "directory": "~/.aws-ssm-calendar/cache",
    "max_size_mb": 100,
    "compression": true,
    "cleanup_interval_hours": 24
  },
  "logging": {
    "level": "INFO",
    "format": "structured",
    "file": "~/.aws-ssm-calendar/logs/application.log",
    "max_size_mb": 10,
    "backup_count": 5,
    "enable_performance_monitoring": true,
    "enable_system_monitoring": true
  },
  "network": {
    "timeout": 30,
    "retry_count": 3,
    "retry_delay": 1,
    "user_agent": "AWS-SSM-Calendar-Tool/1.0",
    "proxy": {
      "http": null,
      "https": null,
      "no_proxy": ["localhost", "127.0.0.1"]
    }
  },
  "performance": {
    "memory_optimization": true,
    "gc_threshold": 1000,
    "concurrent_processing": {
      "enabled": true,
      "max_workers": 4,
      "chunk_size": 100
    }
  },
  "security": {
    "file_permissions": {
      "config": "600",
      "cache": "644",
      "output": "644"
    },
    "encryption": {
      "enabled": false,
      "algorithm": "AES256"
    }
  }
}
```

### 環境変数リファレンス

| 環境変数 | 説明 | デフォルト |
|---------|------|-----------|
| `AWS_SSM_CALENDAR_CONFIG` | 設定ファイルパス | `~/.aws-ssm-calendar/config.json` |
| `AWS_SSM_CALENDAR_CACHE_DIR` | キャッシュディレクトリ | `~/.aws-ssm-calendar/cache` |
| `AWS_SSM_CALENDAR_LOG_LEVEL` | ログレベル | `INFO` |
| `AWS_SSM_CALENDAR_DEBUG` | デバッグモード | `false` |
| `AWS_ACCESS_KEY_ID` | AWSアクセスキーID | - |
| `AWS_SECRET_ACCESS_KEY` | AWSシークレットアクセスキー | - |
| `AWS_SESSION_TOKEN` | AWSセッショントークン | - |
| `AWS_DEFAULT_REGION` | デフォルトリージョン | `ap-northeast-1` |
| `AWS_PROFILE` | 使用するプロファイル | `default` |
| `HTTP_PROXY` | HTTPプロキシ | - |
| `HTTPS_PROXY` | HTTPSプロキシ | - |
| `NO_PROXY` | プロキシ除外 | - |

---

## まとめ

このユーザーマニュアルでは、AWS SSM Change Calendar 休業日スケジュール管理ツールの包括的な使用方法を説明しました。

### 次のステップ

1. **基本機能の習得**: [基本的な使用方法](#基本的な使用方法)から始める
2. **運用環境への適用**: [運用ガイド](#運用ガイド)を参考に本番環境で使用
3. **自動化の実装**: [高度な機能](#高度な機能)でCI/CD統合を実現
4. **継続的な改善**: [監視とアラート](#監視とアラート)で運用品質を向上

### サポートとコミュニティ

- **GitHub Issues**: バグ報告や機能要望
- **ドキュメント**: 最新の技術情報
- **サンプルコード**: 実用的な使用例

効率的で安全な祝日管理システムの構築にお役立てください。