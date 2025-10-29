# サンプルスクリプトと使用例

このディレクトリには、AWS SSM Change Calendar 休業日スケジュール管理ツールの実用的なサンプルスクリプトと使用例が含まれています。

## ディレクトリ構成

```
examples/
├── README.md                          # このファイル
├── basic_usage/                       # 基本的な使用例
│   ├── simple_holiday_check.py        # シンプルな祝日判定
│   ├── generate_yearly_calendar.py    # 年間カレンダー生成
│   └── business_day_calculator.py     # 営業日計算
├── advanced_usage/                    # 高度な使用例
│   ├── batch_calendar_generator.py    # バッチカレンダー生成
│   ├── aws_integration_example.py     # AWS統合例
│   └── performance_optimized.py       # パフォーマンス最適化例
├── integration_examples/              # 他ツールとの統合例
│   ├── terraform_integration/         # Terraform統合
│   ├── github_actions/                # GitHub Actions統合
│   └── docker_deployment/             # Docker展開例
├── configuration/                     # 設定ファイル例
│   ├── config_examples.json           # 設定ファイル例
│   ├── aws_policies.json              # IAMポリシー例
│   └── environment_variables.env      # 環境変数例
└── utilities/                         # ユーティリティスクリプト
    ├── maintenance_scheduler.py        # メンテナンススケジューラー
    ├── monitoring_dashboard.py         # 監視ダッシュボード
    └── data_migration.py               # データ移行ツール
```

## 使用方法

各サンプルスクリプトは独立して実行可能です。必要に応じて、プロジェクトのルートディレクトリから実行してください。

```bash
# 基本的な祝日チェック
python examples/basic_usage/simple_holiday_check.py

# 年間カレンダー生成
python examples/basic_usage/generate_yearly_calendar.py --year 2024

# AWS統合例
python examples/advanced_usage/aws_integration_example.py
```

## 前提条件

- Python 3.8以上
- 必要なパッケージのインストール (`pip install -r requirements.txt`)
- AWS認証情報の設定（AWS統合例を使用する場合）

## サンプルの説明

### 基本的な使用例 (basic_usage/)

初心者向けのシンプルな使用例です。基本的な機能の使い方を学ぶのに適しています。

### 高度な使用例 (advanced_usage/)

パフォーマンス最適化やバッチ処理など、より高度な機能を使用した例です。

### 統合例 (integration_examples/)

他のツールやサービスとの統合方法を示す例です。実際の運用環境での使用を想定しています。

### 設定例 (configuration/)

様々な環境での設定ファイルの例です。本番環境、開発環境、テスト環境での設定を参考にできます。

### ユーティリティ (utilities/)

運用に役立つユーティリティスクリプトです。メンテナンスや監視に使用できます。

## 注意事項

- サンプルスクリプトは教育目的で提供されています
- 本番環境で使用する前に、適切なテストを実施してください
- AWS関連の例では、適切なIAM権限が必要です
- 設定ファイルの例では、実際の値に置き換えてください

## 貢献

新しいサンプルや改善案がある場合は、プルリクエストを送信してください。