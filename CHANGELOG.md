# Changelog

All notable changes to the AWS SSM Change Calendar ICS Generator project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Future enhancements will be listed here

### Changed
- Future changes will be listed here

### Deprecated
- Future deprecations will be listed here

### Removed
- Future removals will be listed here

### Fixed
- Future fixes will be listed here

### Security
- Future security updates will be listed here

## [1.0.0] - 2025-10-30

### Added
- **要件1: 日本祝日データ取得・管理**
  - 内閣府公式CSV（https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv）からの祝日データ自動取得
  - 文字エンコーディング自動検出・UTF-8変換（Shift_JIS/CP932対応）
  - 当年以降祝日データフィルタリング機能
  - 30日間有効期限付きローカルキャッシュシステム（`~/.aws-ssm-calendar/cache/`）
  - データインテグリティ検証機能

- **要件2: AWS SSM Change Calendar用ICS変換**
  - AWS SSM Change Calendar専用ICS形式生成（PRODID: -//AWS//Change Calendar 1.0//EN）
  - 当年以降祝日データのICS変換
  - UTF-8エンコーディング対応（日本語祝日名の正確な表示）
  - 必須イベントプロパティ（UID、DTSTAMP、SUMMARY、DTSTART、DTEND）の自動生成
  - 日曜祝日フィルタリング機能（デフォルト：除外、オプションで包含可能）
  - Asia/Tokyoタイムゾーン定義の自動追加

- **要件3: ICSファイル解析・可視化**
  - ICSファイルの構造化解析機能
  - 人間可読形式での日付順ソート表示
  - 統計情報表示（総イベント数、対象期間、祝日種類別集計）
  - ICS形式エラー検出・報告機能
  - 複数出力形式サポート（標準出力、JSON、CSV、簡易形式）
  - RFC 5545準拠検証機能

- **要件4: ICSファイル比較・差分表示**
  - 2つのICSファイル間のイベントレベル差分検出
  - 時系列ソート表示機能
  - 変更種別表示（追加・削除・変更・未変更）
  - 詳細差分表示（プロパティレベルの変更内容）
  - 変更概要統計（追加X件、削除Y件、変更Z件）

- **要件4.2: イベント意味的Diff形式比較表示**
  - UID主キー + DTSTART/SUMMARY副キー照合による高精度マッチング
  - 意味的diff記号表示（+追加、-削除、~変更、=移動、Δ期間変更）
  - 日付順ソート表示
  - 変更種別統計情報
  - ANSIカラーコード対応（緑=追加、赤=削除、黄=変更、青=移動）

- **要件4.3: AWS Change Calendar統合比較**
  - AWS SSM Change CalendarからのICS内容取得
  - AWS Change CalendarとローカルICSファイルの比較
  - AWS専用比較結果フォーマット
  - 複数AWS Change Calendarのバッチ比較機能
  - 推奨アクション生成機能

- **CLI機能（要件4対応: ユーザビリティとデフォルト設定）**
  - クリーンなデフォルト出力（WARNING レベル、simple フォーマット）
  - 段階的詳細化オプション（--log-level, --enable-monitoring）
  - 包括的コマンドセット：
    - `holidays`: 祝日表示・管理
    - `check-holiday`: 特定日付の祝日確認
    - `refresh-holidays`: 祝日データ強制更新
    - `export`: ICS形式エクスポート
    - `analyze-ics`: ICSファイル解析
    - `compare-ics`: ICSファイル比較
    - `semantic-diff`: 意味的差分表示
    - `create-calendar`: AWS Change Calendar作成
    - `update-calendar`: AWS Change Calendar更新
    - `delete-calendar`: AWS Change Calendar削除
    - `list-calendars`: AWS Change Calendar一覧
    - `analyze-calendar`: AWS Change Calendar解析
    - `compare-calendars`: 複数AWS Change Calendar比較

- **パフォーマンス最適化機能**
  - 遅延読み込み（Lazy Loading）システム
  - 多層キャッシュシステム（メモリ・ファイル・HTTP）
  - メモリ使用量監視・制限機能
  - 効率的なデータ構造（O(1)検索用辞書）
  - ガベージコレクション最適化

- **エラーハンドリング・ログ機能**
  - カスタム例外クラス体系
  - エラー回復戦略・フォールバックメカニズム
  - 構造化ログ（JSON、詳細、シンプル形式）
  - パフォーマンス監視・システムメトリクス
  - デバッグモード・詳細出力制御

- **セキュリティ機能**
  - 入力検証・サニタイゼーション
  - ファイル権限制御（600/644）
  - HTTPS専用ネットワーク接続
  - SSL証明書検証強制
  - パストラバーサル攻撃防止

- **開発・品質保証機能**
  - 包括的テストスイート（ユニット・統合・エンドツーエンド）
  - コード品質ツール（Black、isort、flake8、mypy、bandit）
  - 継続的インテグレーション設定
  - パフォーマンステスト・ベンチマーク
  - コードカバレッジ測定（80%以上）

- **ドキュメント**
  - 包括的README.md（日本語・英語対応）
  - API リファレンスドキュメント
  - コマンドライン使用ガイド
  - アーキテクチャ・設計ドキュメント
  - トラブルシューティングガイド
  - サンプルスクリプト・設定ファイル

### Technical Specifications

- **対応Python バージョン**: 3.8+
- **主要依存関係**:
  - boto3 >= 1.26.0 (AWS SDK)
  - icalendar >= 5.0.0 (ICS処理)
  - click >= 8.0.0 (CLI フレームワーク)
  - requests >= 2.28.0 (HTTP クライアント)
  - psutil >= 5.9.0 (システム監視)

- **パフォーマンス要件**:
  - 祝日検索: < 1ms per query
  - ICS生成: < 100ms for yearly data
  - キャッシュ読み込み: < 50ms
  - メモリ使用量: < 10MB total

- **セキュリティ要件**:
  - HTTPS-only connections
  - Certificate validation enabled
  - Input validation for all user data
  - Restricted file permissions (600/644)

### Architecture

- **モジュラー設計**: 各機能が独立したモジュールとして実装
- **プラガブル アーキテクチャ**: 拡張可能な設計
- **エラーファースト設計**: 堅牢なエラーハンドリング
- **パフォーマンス重視**: 効率的なデータ構造とキャッシュ戦略
- **テスト駆動開発**: 高いテストカバレッジ

### Compatibility

- **AWS Services**: AWS Systems Manager Change Calendar
- **Calendar Applications**: Google Calendar, Outlook, Apple Calendar (標準ICS対応)
- **Operating Systems**: Windows, macOS, Linux
- **Deployment**: Standalone CLI, Docker container ready

## [0.1.0] - 2025-10-29

### Added
- Initial project structure
- Basic CLI framework setup
- Core module scaffolding

---

## Release Notes Format

Each release includes:
- **新機能 (New Features)**: 追加された機能
- **改善 (Improvements)**: 既存機能の改善
- **バグ修正 (Bug Fixes)**: 修正されたバグ
- **破壊的変更 (Breaking Changes)**: 互換性に影響する変更
- **セキュリティ (Security)**: セキュリティ関連の更新
- **パフォーマンス (Performance)**: パフォーマンス改善
- **ドキュメント (Documentation)**: ドキュメント更新

## Migration Guide

### From 0.x to 1.0.0

1. **CLI デフォルト設定変更**:
   - デフォルトログレベル: INFO → WARNING
   - デフォルトログフォーマット: detailed → simple
   - システム監視: デフォルト有効 → デフォルト無効

2. **移行手順**:
   ```bash
   # 従来の詳細出力が必要な場合
   aws-ssm-calendar --log-level INFO --enable-monitoring holidays
   
   # 開発・デバッグ時
   aws-ssm-calendar --debug --log-format structured --enable-monitoring holidays
   ```

3. **新機能の活用**:
   - 意味的diff比較: `aws-ssm-calendar semantic-diff old.ics new.ics`
   - AWS Change Calendar統合: `aws-ssm-calendar compare-calendars cal1 cal2`
   - ICS解析: `aws-ssm-calendar analyze-ics calendar.ics --format json`

## Support

- **Issues**: [GitHub Issues](https://github.com/aws-ssm-calendar-generator/issues)
- **Documentation**: [Project Documentation](https://github.com/aws-ssm-calendar-generator/docs)
- **Discussions**: [GitHub Discussions](https://github.com/aws-ssm-calendar-generator/discussions)