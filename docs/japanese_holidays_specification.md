# 日本の祝日取得機能 仕様書

## 概要

AWS SSM Change Calendar ICS Generatorに組み込まれた日本の祝日取得・管理機能の詳細仕様書です。

## 1. 機能概要

### 1.1 目的
- 日本の国民の祝日・休日データを自動取得・管理
- ICSカレンダーファイルへの祝日統合
- 祝日の検索・確認機能の提供

### 1.2 データソース
- **プライマリ**: 内閣府公式祝日CSV（https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv）
- **フォールバック**: 基本祝日のハードコードデータ

## 2. アーキテクチャ

### 2.1 クラス構成

```
JapaneseHolidays
├── データ取得・管理
├── キャッシュ機能
├── 祝日検索・判定
└── 統計情報提供
```

### 2.2 依存関係
- `requests`: HTTP通信（祝日データ取得）
- `csv`: CSVファイル処理
- `datetime`: 日付処理
- `pathlib`: ファイルパス管理

## 3. 詳細仕様

### 3.1 JapaneseHolidays クラス

#### 3.1.1 初期化
```python
def __init__(self, cache_file: Optional[str] = None)
```

**パラメータ**:
- `cache_file`: キャッシュファイルパス（省略時: `~/.aws-ssm-calendar/cache/japanese_holidays.csv`）

**動作**:
1. キャッシュファイルパスの設定
2. 祝日データの自動読み込み
3. キャッシュの有効性確認（30日以内）

#### 3.1.2 データ取得メソッド

##### `_download_and_cache()`
**機能**: 内閣府から祝日データをダウンロードしてキャッシュ

**処理フロー**:
1. HTTP GETリクエスト（タイムアウト: 30秒）
2. 文字エンコーディング自動判定（shift_jis, cp932, utf-8）
3. CSVパース処理
4. ローカルキャッシュ保存
5. エラー時フォールバックデータ使用

**エラーハンドリング**:
- ネットワークエラー → フォールバックデータ
- エンコーディングエラー → 複数エンコーディング試行
- パースエラー → 行スキップ継続

##### `_load_from_cache()`
**機能**: キャッシュファイルから祝日データを読み込み

**処理**:
1. UTF-8エンコーディングでCSV読み込み
2. ヘッダー行スキップ
3. 日付フォーマット検証（YYYY/MM/DD）
4. 辞書形式でデータ格納

##### `_use_fallback_data()`
**機能**: ネットワーク障害時の基本祝日データ提供

**含まれる祝日**:
- 元日（1/1）
- 建国記念の日（2/11）
- 昭和の日（4/29）
- 憲法記念日（5/3）
- みどりの日（5/4）
- こどもの日（5/5）
- 山の日（8/11）
- 文化の日（11/3）
- 勤労感謝の日（11/23）

#### 3.1.3 祝日検索・判定メソッド

##### `is_holiday(check_date: date) -> bool`
**機能**: 指定日が祝日かどうかを判定

**パラメータ**:
- `check_date`: 確認対象の日付

**戻り値**: 祝日の場合True、平日の場合False

##### `get_holiday_name(check_date: date) -> Optional[str]`
**機能**: 指定日の祝日名を取得

**戻り値**: 祝日名（祝日でない場合はNone）

##### `get_holidays_in_range(start_date: date, end_date: date) -> List[Tuple[date, str]]`
**機能**: 指定期間内の祝日一覧を取得

**パラメータ**:
- `start_date`: 開始日（含む）
- `end_date`: 終了日（含む）

**戻り値**: (日付, 祝日名) のタプルリスト（日付順ソート済み）

##### `get_holidays_by_year(year: int) -> List[Tuple[date, str]]`
**機能**: 指定年の祝日一覧を取得

**実装**: `get_holidays_in_range()`のラッパー

##### `get_next_holiday(from_date: Optional[date] = None) -> Optional[Tuple[date, str]]`
**機能**: 指定日以降の次の祝日を取得

**パラメータ**:
- `from_date`: 基準日（省略時: 今日）

**戻り値**: 次の祝日の(日付, 祝日名)、見つからない場合None

#### 3.1.4 管理・統計メソッド

##### `refresh_data()`
**機能**: 祝日データの強制更新

**処理**: キャッシュを無視して内閣府から最新データを取得

##### `get_stats() -> Dict[str, int]`
**機能**: 読み込み済み祝日データの統計情報を取得

**戻り値**:
```python
{
    'total': int,      # 総祝日数
    'years': int,      # 対象年数
    'min_year': int,   # 最古年
    'max_year': int    # 最新年
}
```

### 3.2 キャッシュ仕様

#### 3.2.1 キャッシュファイル
- **場所**: `~/.aws-ssm-calendar/cache/japanese_holidays.csv`
- **フォーマット**: UTF-8 CSV
- **構造**:
  ```csv
  国民の祝日・休日月日,国民の祝日・休日名称
  2024/01/01,元日
  2024/01/08,成人の日
  ...
  ```

#### 3.2.2 キャッシュ有効期限
- **期限**: 30日
- **判定**: ファイル更新日時ベース
- **期限切れ時**: 自動再ダウンロード

#### 3.2.3 キャッシュ管理
- **自動作成**: 初回実行時
- **自動更新**: 期限切れ時
- **手動更新**: `refresh_data()`メソッド

## 4. ICS統合仕様

### 4.1 ICSGenerator統合

#### 4.1.1 初期化オプション
```python
ICSGenerator(include_japanese_holidays: bool = False)
```

#### 4.1.2 祝日追加メソッド

##### `add_japanese_holidays(start_date: date, end_date: date)`
**機能**: 指定期間の祝日をカレンダーに追加

**イベント仕様**:
- **タイトル**: `🎌 {祝日名}`
- **種別**: 全日イベント（VALUE=DATE）
- **開始日**: 祝日当日
- **終了日**: 祝日翌日（ICS標準準拠）
- **説明**: `日本の祝日: {祝日名}`
- **カテゴリ**: `Japanese-Holiday`
- **UID**: `{日付}-japanese-holiday@aws-ssm-change-calendar`

##### `add_japanese_holidays_for_year(year: int)`
**機能**: 指定年の全祝日をカレンダーに追加

**実装**: `add_japanese_holidays()`のラッパー

### 4.2 ICSファイル出力仕様

#### 4.2.1 ファイル形式
- **標準**: RFC 5545 (iCalendar)
- **エンコーディング**: UTF-8
- **拡張子**: `.ics`

#### 4.2.2 イベント属性
```
BEGIN:VEVENT
SUMMARY:🎌 元日
DTSTART;VALUE=DATE:20240101
DTEND;VALUE=DATE:20240102
DTSTAMP:20241024T043636Z
UID:2024-01-01-japanese-holiday@aws-ssm-change-calendar
CATEGORIES:Japanese-Holiday
DESCRIPTION:日本の祝日: 元日
END:VEVENT
```

## 5. CLI仕様

### 5.1 祝日関連コマンド

#### 5.1.1 `holidays`
**機能**: 祝日の表示・エクスポート

**構文**:
```bash
python main.py holidays [OPTIONS]
```

**オプション**:
- `-y, --year INTEGER`: 対象年（デフォルト: 現在年）
- `-o, --output TEXT`: 出力ICSファイルパス

**出力例**:
```
Japanese holidays for 2024:
  2024-01-01 (Mon) - 元日
  2024-01-08 (Mon) - 成人の日
  ...
```

#### 5.1.2 `check-holiday`
**機能**: 特定日の祝日判定

**構文**:
```bash
python main.py check-holiday [OPTIONS]
```

**オプション**:
- `-d, --date TEXT`: 確認日（YYYY-MM-DD、デフォルト: 今日）

**出力例**:
```
2024-01-01 is a Japanese holiday: 元日
Next holiday: 2024-01-08 (成人の日) in 7 days
```

#### 5.1.3 `refresh-holidays`
**機能**: 祝日データの強制更新

**構文**:
```bash
python main.py refresh-holidays
```

**出力例**:
```
Successfully refreshed holidays data:
  Total holidays: 1050
  Years covered: 72 (1955-2026)
```

#### 5.1.4 `export` (祝日統合オプション)
**機能**: Change Calendarと祝日の統合エクスポート

**追加オプション**:
- `--include-holidays`: 祝日を含める
- `--holidays-year INTEGER`: 祝日対象年

**例**:
```bash
python main.py export MyCalendar --include-holidays --holidays-year 2024 -o calendar.ics
```

## 6. エラーハンドリング

### 6.1 ネットワークエラー
- **タイムアウト**: 30秒
- **リトライ**: なし（フォールバックデータ使用）
- **エラーメッセージ**: コンソール出力

### 6.2 ファイルI/Oエラー
- **キャッシュ読み込み失敗**: 再ダウンロード実行
- **キャッシュ書き込み失敗**: 警告表示、処理継続
- **ICS保存失敗**: UTF-8テキストモードでフォールバック

### 6.3 データ形式エラー
- **CSV解析エラー**: 該当行スキップ
- **日付形式エラー**: 該当行スキップ
- **文字エンコーディングエラー**: 複数エンコーディング試行

## 7. パフォーマンス仕様

### 7.1 メモリ使用量
- **祝日データ**: 約1,050件 × 50バイト = 52KB
- **キャッシュファイル**: 約30KB
- **総メモリ**: 100KB未満

### 7.2 処理時間
- **初回ダウンロード**: 1-3秒（ネットワーク依存）
- **キャッシュ読み込み**: 10-50ms
- **祝日判定**: 1ms未満
- **ICS生成**: 年間祝日で10-50ms

### 7.3 ディスク使用量
- **キャッシュファイル**: 30KB
- **ICSファイル**: 年間祝日で5KB

## 8. セキュリティ仕様

### 8.1 データソース
- **HTTPS通信**: 内閣府公式サイト
- **証明書検証**: 有効
- **データ検証**: 日付形式チェック

### 8.2 ファイルアクセス
- **キャッシュディレクトリ**: ユーザーホーム配下
- **ファイル権限**: ユーザー読み書きのみ
- **パストラバーサル対策**: pathlib使用

## 9. 互換性

### 9.1 Python バージョン
- **対応**: Python 3.8+
- **テスト済み**: 3.8, 3.9, 3.10, 3.11

### 9.2 依存ライブラリ
- `requests >= 2.28.0`
- `python-dateutil >= 2.8.0`
- `icalendar >= 5.0.0`

### 9.3 カレンダーアプリ互換性
- Google Calendar: ✅
- Microsoft Outlook: ✅
- Apple Calendar: ✅
- Thunderbird: ✅

## 10. 今後の拡張予定

### 10.1 機能拡張
- [ ] 地方自治体独自祝日対応
- [ ] カスタム祝日・記念日追加
- [ ] 多言語対応（英語名）
- [ ] 祝日統計・分析機能

### 10.2 パフォーマンス改善
- [ ] 非同期ダウンロード
- [ ] 差分更新機能
- [ ] メモリ使用量最適化

### 10.3 統合機能
- [ ] 他カレンダーサービスAPI連携
- [ ] Webhook通知機能
- [ ] 祝日変更履歴管理