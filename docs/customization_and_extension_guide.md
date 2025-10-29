# 🔧 カスタマイズ・拡張ガイド

## 📋 概要

AWS SSM Change Calendar 休業日スケジュール管理ツールをカスタマイズし、独自の要件に合わせて拡張する方法を詳しく説明します。

## 🎯 対象読者

- **システム統合者**: 既存システムとの連携を実装したい方
- **開発者**: 独自機能を追加したい方
- **DevOpsエンジニア**: 自動化ワークフローに組み込みたい方
- **企業ユーザー**: 組織固有の要件に対応したい方

---

## 🏗️ カスタマイズ可能な領域

### 1. 祝日データソース
- 他国の祝日システム
- 企業独自の休業日
- 地域固有の祝日

### 2. 出力形式
- カスタムファイル形式
- API レスポンス形式
- レポート形式

### 3. AWS統合
- 他のAWSサービス連携
- カスタムChange Calendar形式
- 独自の認証方式

### 4. ユーザーインターフェース
- Web UI
- REST API
- GraphQL API

---

## 🌍 他国の祝日システム追加

### 基本実装

```python
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class Holiday:
    date: date
    name: str
    category: str = "national"
    is_substitute: bool = False
    description: Optional[str] = None

class HolidayProvider(ABC):
    """祝日プロバイダーの基底クラス"""
    
    @abstractmethod
    def get_holidays(self, year: int) -> List[Holiday]:
        """指定年の祝日を取得"""
        pass
    
    @abstractmethod
    def is_holiday(self, check_date: date) -> bool:
        """祝日判定"""
        pass
    
    @abstractmethod
    def get_country_code(self) -> str:
        """国コードを取得"""
        pass
```

### アメリカの祝日実装例

```python
from dateutil.relativedelta import relativedelta
from dateutil.easter import easter

class USHolidays(HolidayProvider):
    """アメリカ連邦祝日プロバイダー"""
    
    def __init__(self):
        self._cache: Dict[int, List[Holiday]] = {}
    
    def get_country_code(self) -> str:
        return "US"
    
    def get_holidays(self, year: int) -> List[Holiday]:
        """アメリカの連邦祝日を計算"""
        if year in self._cache:
            return self._cache[year]
        
        holidays = []
        
        # New Year's Day (1月1日)
        holidays.append(Holiday(
            date=date(year, 1, 1),
            name="New Year's Day",
            category="federal"
        ))
        
        # Martin Luther King Jr. Day (1月第3月曜日)
        mlk_day = self._nth_weekday(year, 1, 0, 3)  # 3rd Monday
        holidays.append(Holiday(
            date=mlk_day,
            name="Martin Luther King Jr. Day",
            category="federal"
        ))
        
        # Presidents' Day (2月第3月曜日)
        presidents_day = self._nth_weekday(year, 2, 0, 3)
        holidays.append(Holiday(
            date=presidents_day,
            name="Presidents' Day",
            category="federal"
        ))
        
        # Memorial Day (5月最終月曜日)
        memorial_day = self._last_weekday(year, 5, 0)  # Last Monday
        holidays.append(Holiday(
            date=memorial_day,
            name="Memorial Day",
            category="federal"
        ))
        
        # Independence Day (7月4日)
        holidays.append(Holiday(
            date=date(year, 7, 4),
            name="Independence Day",
            category="federal"
        ))
        
        # Labor Day (9月第1月曜日)
        labor_day = self._nth_weekday(year, 9, 0, 1)
        holidays.append(Holiday(
            date=labor_day,
            name="Labor Day",
            category="federal"
        ))
        
        # Columbus Day (10月第2月曜日)
        columbus_day = self._nth_weekday(year, 10, 0, 2)
        holidays.append(Holiday(
            date=columbus_day,
            name="Columbus Day",
            category="federal"
        ))
        
        # Veterans Day (11月11日)
        holidays.append(Holiday(
            date=date(year, 11, 11),
            name="Veterans Day",
            category="federal"
        ))
        
        # Thanksgiving (11月第4木曜日)
        thanksgiving = self._nth_weekday(year, 11, 3, 4)  # 4th Thursday
        holidays.append(Holiday(
            date=thanksgiving,
            name="Thanksgiving Day",
            category="federal"
        ))
        
        # Christmas Day (12月25日)
        holidays.append(Holiday(
            date=date(year, 12, 25),
            name="Christmas Day",
            category="federal"
        ))
        
        # 振替休日の処理
        holidays = self._handle_substitutes(holidays)
        
        self._cache[year] = holidays
        return holidays
    
    def is_holiday(self, check_date: date) -> bool:
        year_holidays = self.get_holidays(check_date.year)
        return check_date in [h.date for h in year_holidays]
    
    def _nth_weekday(self, year: int, month: int, weekday: int, n: int) -> date:
        """月のn番目の指定曜日を取得"""
        first_day = date(year, month, 1)
        first_weekday = first_day.weekday()
        
        # 最初の指定曜日までの日数
        days_to_first = (weekday - first_weekday) % 7
        first_occurrence = first_day + relativedelta(days=days_to_first)
        
        # n番目の発生日
        return first_occurrence + relativedelta(weeks=n-1)
    
    def _last_weekday(self, year: int, month: int, weekday: int) -> date:
        """月の最後の指定曜日を取得"""
        # 翌月の1日から逆算
        next_month = date(year, month, 1) + relativedelta(months=1)
        last_day = next_month - relativedelta(days=1)
        
        # 最後の指定曜日までの日数
        days_back = (last_day.weekday() - weekday) % 7
        return last_day - relativedelta(days=days_back)
    
    def _handle_substitutes(self, holidays: List[Holiday]) -> List[Holiday]:
        """振替休日の処理"""
        result = []
        
        for holiday in holidays:
            result.append(holiday)
            
            # 土日の場合は振替休日を追加
            if holiday.date.weekday() == 5:  # Saturday
                substitute = Holiday(
                    date=holiday.date + relativedelta(days=2),  # Monday
                    name=f"{holiday.name} (Observed)",
                    category="substitute",
                    is_substitute=True
                )
                result.append(substitute)
            elif holiday.date.weekday() == 6:  # Sunday
                substitute = Holiday(
                    date=holiday.date + relativedelta(days=1),  # Monday
                    name=f"{holiday.name} (Observed)",
                    category="substitute",
                    is_substitute=True
                )
                result.append(substitute)
        
        return result
```

### イギリスの祝日実装例

```python
class UKHolidays(HolidayProvider):
    """イギリスの祝日プロバイダー"""
    
    def get_country_code(self) -> str:
        return "UK"
    
    def get_holidays(self, year: int) -> List[Holiday]:
        holidays = []
        
        # New Year's Day
        holidays.append(Holiday(
            date=date(year, 1, 1),
            name="New Year's Day",
            category="bank_holiday"
        ))
        
        # Good Friday (復活祭の2日前)
        easter_date = easter(year)
        good_friday = easter_date - relativedelta(days=2)
        holidays.append(Holiday(
            date=good_friday,
            name="Good Friday",
            category="bank_holiday"
        ))
        
        # Easter Monday (復活祭の翌日)
        easter_monday = easter_date + relativedelta(days=1)
        holidays.append(Holiday(
            date=easter_monday,
            name="Easter Monday",
            category="bank_holiday"
        ))
        
        # Early May Bank Holiday (5月第1月曜日)
        early_may = self._nth_weekday(year, 5, 0, 1)
        holidays.append(Holiday(
            date=early_may,
            name="Early May Bank Holiday",
            category="bank_holiday"
        ))
        
        # Spring Bank Holiday (5月最終月曜日)
        spring_bank = self._last_weekday(year, 5, 0)
        holidays.append(Holiday(
            date=spring_bank,
            name="Spring Bank Holiday",
            category="bank_holiday"
        ))
        
        # Summer Bank Holiday (8月最終月曜日)
        summer_bank = self._last_weekday(year, 8, 0)
        holidays.append(Holiday(
            date=summer_bank,
            name="Summer Bank Holiday",
            category="bank_holiday"
        ))
        
        # Christmas Day
        holidays.append(Holiday(
            date=date(year, 12, 25),
            name="Christmas Day",
            category="bank_holiday"
        ))
        
        # Boxing Day
        holidays.append(Holiday(
            date=date(year, 12, 26),
            name="Boxing Day",
            category="bank_holiday"
        ))
        
        return self._handle_substitutes(holidays)
    
    # _nth_weekday, _last_weekday, _handle_substitutes メソッドは
    # USHolidays と同様の実装
```

### プロバイダーファクトリーの拡張

```python
class HolidayProviderFactory:
    """祝日プロバイダーのファクトリー"""
    
    _providers: Dict[str, Type[HolidayProvider]] = {
        'japan': JapaneseHolidays,
        'us': USHolidays,
        'uk': UKHolidays,
    }
    
    @classmethod
    def create(cls, country: str, **kwargs) -> HolidayProvider:
        """プロバイダーを作成"""
        country = country.lower()
        if country not in cls._providers:
            available = ', '.join(cls._providers.keys())
            raise ValueError(f"Unsupported country: {country}. Available: {available}")
        
        return cls._providers[country](**kwargs)
    
    @classmethod
    def register(cls, country: str, provider_class: Type[HolidayProvider]):
        """新しいプロバイダーを登録"""
        cls._providers[country.lower()] = provider_class
    
    @classmethod
    def list_countries(cls) -> List[str]:
        """サポートされている国のリストを取得"""
        return list(cls._providers.keys())

# 使用例
# アメリカの祝日
us_holidays = HolidayProviderFactory.create('us')
print(us_holidays.get_holidays(2024))

# イギリスの祝日
uk_holidays = HolidayProviderFactory.create('uk')
print(uk_holidays.is_holiday(date(2024, 12, 25)))
```

---

## 🏢 企業固有の休業日システム

### 企業休業日プロバイダー

```python
from typing import Set
import json

class CorporateHolidays(HolidayProvider):
    """企業固有の休業日プロバイダー"""
    
    def __init__(self, config_file: str, base_provider: Optional[HolidayProvider] = None):
        self.config_file = config_file
        self.base_provider = base_provider or JapaneseHolidays()
        self.corporate_config = self._load_config()
    
    def get_country_code(self) -> str:
        return f"{self.base_provider.get_country_code()}_CORP"
    
    def _load_config(self) -> Dict:
        """企業設定を読み込み"""
        with open(self.config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_holidays(self, year: int) -> List[Holiday]:
        """企業の休業日を取得"""
        holidays = []
        
        # 基本祝日を取得
        if self.base_provider:
            base_holidays = self.base_provider.get_holidays(year)
            
            # 除外祝日の処理
            excluded_dates = set(self._parse_dates(
                self.corporate_config.get('excluded_holidays', []), year
            ))
            
            for holiday in base_holidays:
                if holiday.date not in excluded_dates:
                    holidays.append(holiday)
        
        # 企業固有の休業日を追加
        corporate_holidays = self._get_corporate_holidays(year)
        holidays.extend(corporate_holidays)
        
        # 創立記念日などの固定日を追加
        fixed_holidays = self._get_fixed_corporate_holidays(year)
        holidays.extend(fixed_holidays)
        
        return sorted(holidays, key=lambda h: h.date)
    
    def _get_corporate_holidays(self, year: int) -> List[Holiday]:
        """企業固有の休業日を取得"""
        holidays = []
        
        # 夏季休暇
        summer_vacation = self.corporate_config.get('summer_vacation', {})
        if summer_vacation.get('enabled', False):
            start_date = self._parse_date(summer_vacation['start'], year)
            end_date = self._parse_date(summer_vacation['end'], year)
            
            current_date = start_date
            while current_date <= end_date:
                holidays.append(Holiday(
                    date=current_date,
                    name="夏季休暇",
                    category="corporate"
                ))
                current_date += relativedelta(days=1)
        
        # 年末年始休暇
        year_end_vacation = self.corporate_config.get('year_end_vacation', {})
        if year_end_vacation.get('enabled', False):
            # 年末
            end_start = self._parse_date(year_end_vacation['end_start'], year)
            end_end = date(year, 12, 31)
            
            current_date = end_start
            while current_date <= end_end:
                holidays.append(Holiday(
                    date=current_date,
                    name="年末休暇",
                    category="corporate"
                ))
                current_date += relativedelta(days=1)
            
            # 年始
            new_year_start = date(year, 1, 1)
            new_year_end = self._parse_date(year_end_vacation['new_year_end'], year)
            
            current_date = new_year_start
            while current_date <= new_year_end:
                holidays.append(Holiday(
                    date=current_date,
                    name="年始休暇",
                    category="corporate"
                ))
                current_date += relativedelta(days=1)
        
        return holidays
    
    def _get_fixed_corporate_holidays(self, year: int) -> List[Holiday]:
        """固定の企業休業日を取得"""
        holidays = []
        
        fixed_holidays = self.corporate_config.get('fixed_holidays', [])
        for fixed_holiday in fixed_holidays:
            holiday_date = self._parse_date(fixed_holiday['date'], year)
            holidays.append(Holiday(
                date=holiday_date,
                name=fixed_holiday['name'],
                category="corporate",
                description=fixed_holiday.get('description')
            ))
        
        return holidays
    
    def _parse_date(self, date_str: str, year: int) -> date:
        """日付文字列を解析"""
        if isinstance(date_str, str):
            if date_str.startswith('YYYY-'):
                # YYYY-MM-DD 形式
                month_day = date_str[5:]
                return datetime.strptime(f"{year}-{month_day}", "%Y-%m-%d").date()
            else:
                # 完全な日付
                return datetime.strptime(date_str, "%Y-%m-%d").date()
        return date_str
    
    def _parse_dates(self, date_list: List[str], year: int) -> List[date]:
        """日付リストを解析"""
        return [self._parse_date(date_str, year) for date_str in date_list]
    
    def is_holiday(self, check_date: date) -> bool:
        year_holidays = self.get_holidays(check_date.year)
        return check_date in [h.date for h in year_holidays]
```

### 企業設定ファイル例

```json
{
  "company_name": "株式会社サンプル",
  "base_country": "japan",
  "excluded_holidays": [
    "YYYY-02-11",
    "YYYY-04-29"
  ],
  "summer_vacation": {
    "enabled": true,
    "start": "YYYY-08-13",
    "end": "YYYY-08-16",
    "description": "夏季休暇期間"
  },
  "year_end_vacation": {
    "enabled": true,
    "end_start": "YYYY-12-29",
    "new_year_end": "YYYY-01-03",
    "description": "年末年始休暇"
  },
  "fixed_holidays": [
    {
      "date": "YYYY-06-15",
      "name": "創立記念日",
      "description": "会社創立記念日"
    },
    {
      "date": "YYYY-11-30",
      "name": "決算日",
      "description": "決算処理のため休業"
    }
  ],
  "flexible_holidays": {
    "enabled": true,
    "annual_count": 5,
    "description": "年間5日の自由休暇"
  }
}
```

---

## 📊 カスタム出力形式の追加

### 出力フォーマッターの基底クラス

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class OutputFormatter(ABC):
    """出力フォーマッターの基底クラス"""
    
    @abstractmethod
    def format_holidays(self, holidays: List[Holiday], **kwargs) -> str:
        """祝日リストをフォーマット"""
        pass
    
    @abstractmethod
    def get_content_type(self) -> str:
        """コンテンツタイプを取得"""
        pass
    
    @abstractmethod
    def get_file_extension(self) -> str:
        """ファイル拡張子を取得"""
        pass
```

### Excel形式フォーマッター

```python
import pandas as pd
from io import BytesIO

class ExcelFormatter(OutputFormatter):
    """Excel形式フォーマッター"""
    
    def format_holidays(self, holidays: List[Holiday], **kwargs) -> bytes:
        """Excel形式で祝日を出力"""
        
        # DataFrameを作成
        data = []
        for holiday in holidays:
            data.append({
                '日付': holiday.date,
                '曜日': self._get_weekday_japanese(holiday.date),
                '祝日名': holiday.name,
                'カテゴリ': holiday.category,
                '振替休日': '○' if holiday.is_substitute else '',
                '説明': holiday.description or ''
            })
        
        df = pd.DataFrame(data)
        
        # Excelファイルを作成
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='祝日一覧', index=False)
            
            # スタイリング
            workbook = writer.book
            worksheet = writer.sheets['祝日一覧']
            
            # ヘッダーのスタイル
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            
            for cell in worksheet[1]:
                cell.font = header_font
                cell.fill = header_fill
            
            # 列幅の調整
            column_widths = {
                'A': 12,  # 日付
                'B': 8,   # 曜日
                'C': 20,  # 祝日名
                'D': 12,  # カテゴリ
                'E': 8,   # 振替休日
                'F': 30   # 説明
            }
            
            for column, width in column_widths.items():
                worksheet.column_dimensions[column].width = width
        
        output.seek(0)
        return output.getvalue()
    
    def _get_weekday_japanese(self, date_obj: date) -> str:
        """日本語の曜日を取得"""
        weekdays = ['月', '火', '水', '木', '金', '土', '日']
        return weekdays[date_obj.weekday()]
    
    def get_content_type(self) -> str:
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    
    def get_file_extension(self) -> str:
        return "xlsx"
```

### PDF形式フォーマッター

```python
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO

class PDFFormatter(OutputFormatter):
    """PDF形式フォーマッター"""
    
    def __init__(self):
        # 日本語フォントの登録
        try:
            pdfmetrics.registerFont(TTFont('NotoSansCJK', 'NotoSansCJK-Regular.ttf'))
            self.font_name = 'NotoSansCJK'
        except:
            self.font_name = 'Helvetica'  # フォールバック
    
    def format_holidays(self, holidays: List[Holiday], **kwargs) -> bytes:
        """PDF形式で祝日を出力"""
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        
        # スタイルの設定
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName=self.font_name,
            fontSize=18,
            alignment=1,  # 中央揃え
            spaceAfter=30
        )
        
        # コンテンツの構築
        story = []
        
        # タイトル
        year = holidays[0].date.year if holidays else datetime.now().year
        title = Paragraph(f"{year}年 祝日一覧", title_style)
        story.append(title)
        story.append(Spacer(1, 20))
        
        # テーブルデータの準備
        table_data = [['日付', '曜日', '祝日名', 'カテゴリ']]
        
        for holiday in holidays:
            table_data.append([
                holiday.date.strftime('%Y-%m-%d'),
                self._get_weekday_japanese(holiday.date),
                holiday.name,
                holiday.category
            ])
        
        # テーブルの作成
        table = Table(table_data, colWidths=[80, 40, 150, 80])
        table.setStyle(TableStyle([
            # ヘッダーのスタイル
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), self.font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            
            # データ行のスタイル
            ('FONTNAME', (0, 1), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # 交互の行の背景色
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        
        story.append(table)
        
        # 統計情報
        story.append(Spacer(1, 30))
        stats_style = ParagraphStyle(
            'Stats',
            parent=styles['Normal'],
            fontName=self.font_name,
            fontSize=10
        )
        
        total_holidays = len(holidays)
        weekend_holidays = len([h for h in holidays if h.date.weekday() >= 5])
        
        stats_text = f"""
        <b>統計情報:</b><br/>
        • 総祝日数: {total_holidays}日<br/>
        • 土日の祝日: {weekend_holidays}日<br/>
        • 平日の祝日: {total_holidays - weekend_holidays}日
        """
        
        stats = Paragraph(stats_text, stats_style)
        story.append(stats)
        
        # PDFの生成
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    
    def _get_weekday_japanese(self, date_obj: date) -> str:
        """日本語の曜日を取得"""
        weekdays = ['月', '火', '水', '木', '金', '土', '日']
        return weekdays[date_obj.weekday()]
    
    def get_content_type(self) -> str:
        return "application/pdf"
    
    def get_file_extension(self) -> str:
        return "pdf"
```

### HTML形式フォーマッター

```python
from jinja2 import Template

class HTMLFormatter(OutputFormatter):
    """HTML形式フォーマッター"""
    
    def __init__(self):
        self.template = Template("""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ year }}年 祝日一覧</title>
    <style>
        body {
            font-family: 'Hiragino Sans', 'Yu Gothic', 'Meiryo', sans-serif;
            margin: 40px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 30px;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 30px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #4CAF50;
            color: white;
            font-weight: bold;
        }
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .weekend {
            color: #e74c3c;
            font-weight: bold;
        }
        .substitute {
            background-color: #fff3cd;
        }
        .stats {
            background-color: #e8f5e8;
            padding: 20px;
            border-radius: 5px;
            border-left: 4px solid #4CAF50;
        }
        .stats h3 {
            margin-top: 0;
            color: #2e7d32;
        }
        .category-national { color: #d32f2f; }
        .category-substitute { color: #f57c00; }
        .category-corporate { color: #7b1fa2; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎌 {{ year }}年 祝日一覧</h1>
        
        <table>
            <thead>
                <tr>
                    <th>日付</th>
                    <th>曜日</th>
                    <th>祝日名</th>
                    <th>カテゴリ</th>
                </tr>
            </thead>
            <tbody>
                {% for holiday in holidays %}
                <tr class="{% if holiday.is_substitute %}substitute{% endif %}">
                    <td>{{ holiday.date.strftime('%Y-%m-%d') }}</td>
                    <td class="{% if holiday.date.weekday() >= 5 %}weekend{% endif %}">
                        {{ weekdays[holiday.date.weekday()] }}
                    </td>
                    <td>{{ holiday.name }}</td>
                    <td class="category-{{ holiday.category }}">{{ holiday.category }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        
        <div class="stats">
            <h3>📊 統計情報</h3>
            <ul>
                <li><strong>総祝日数:</strong> {{ stats.total }}日</li>
                <li><strong>土日の祝日:</strong> {{ stats.weekend }}日 ({{ "%.1f"|format(stats.weekend_percent) }}%)</li>
                <li><strong>平日の祝日:</strong> {{ stats.weekday }}日 ({{ "%.1f"|format(stats.weekday_percent) }}%)</li>
                <li><strong>振替休日:</strong> {{ stats.substitute }}日</li>
            </ul>
        </div>
        
        <div style="text-align: center; margin-top: 30px; color: #666; font-size: 12px;">
            Generated by AWS SSM Calendar ICS Generator
        </div>
    </div>
</body>
</html>
        """)
    
    def format_holidays(self, holidays: List[Holiday], **kwargs) -> str:
        """HTML形式で祝日を出力"""
        
        if not holidays:
            return "<html><body><h1>祝日データがありません</h1></body></html>"
        
        year = holidays[0].date.year
        weekdays = ['月', '火', '水', '木', '金', '土', '日']
        
        # 統計計算
        total = len(holidays)
        weekend = len([h for h in holidays if h.date.weekday() >= 5])
        weekday = total - weekend
        substitute = len([h for h in holidays if h.is_substitute])
        
        stats = {
            'total': total,
            'weekend': weekend,
            'weekday': weekday,
            'substitute': substitute,
            'weekend_percent': (weekend / total * 100) if total > 0 else 0,
            'weekday_percent': (weekday / total * 100) if total > 0 else 0
        }
        
        return self.template.render(
            year=year,
            holidays=holidays,
            weekdays=weekdays,
            stats=stats
        )
    
    def get_content_type(self) -> str:
        return "text/html"
    
    def get_file_extension(self) -> str:
        return "html"
```

### フォーマッターレジストリの拡張

```python
class FormatterRegistry:
    """フォーマッターの登録・管理"""
    
    _formatters: Dict[str, Type[OutputFormatter]] = {
        'json': JSONFormatter,
        'csv': CSVFormatter,
        'xml': XMLFormatter,
        'html': HTMLFormatter,
        'pdf': PDFFormatter,
        'excel': ExcelFormatter,
    }
    
    @classmethod
    def get_formatter(cls, format_name: str) -> OutputFormatter:
        """フォーマッターを取得"""
        format_name = format_name.lower()
        if format_name not in cls._formatters:
            available = ', '.join(cls._formatters.keys())
            raise ValueError(f"Unknown format: {format_name}. Available: {available}")
        
        return cls._formatters[format_name]()
    
    @classmethod
    def register(cls, format_name: str, formatter_class: Type[OutputFormatter]):
        """新しいフォーマッターを登録"""
        cls._formatters[format_name.lower()] = formatter_class
    
    @classmethod
    def list_formats(cls) -> List[str]:
        """利用可能な形式のリストを取得"""
        return list(cls._formatters.keys())
    
    @classmethod
    def format_holidays(cls, holidays: List[Holiday], format_name: str, **kwargs) -> Any:
        """祝日をフォーマット"""
        formatter = cls.get_formatter(format_name)
        return formatter.format_holidays(holidays, **kwargs)

# 使用例
holidays = JapaneseHolidays().get_holidays(2024)

# HTML形式で出力
html_content = FormatterRegistry.format_holidays(holidays, 'html')
with open('holidays_2024.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

# PDF形式で出力
pdf_content = FormatterRegistry.format_holidays(holidays, 'pdf')
with open('holidays_2024.pdf', 'wb') as f:
    f.write(pdf_content)

# Excel形式で出力
excel_content = FormatterRegistry.format_holidays(holidays, 'excel')
with open('holidays_2024.xlsx', 'wb') as f:
    f.write(excel_content)
```

---

## 🌐 Web API の追加

### Flask ベースの REST API

```python
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from datetime import datetime
import io

app = Flask(__name__)
CORS(app)

class HolidayAPI:
    """祝日API クラス"""
    
    def __init__(self):
        self.holiday_factory = HolidayProviderFactory()
        self.formatter_registry = FormatterRegistry()
    
    def get_holidays(self, country: str, year: int, format_type: str = 'json'):
        """祝日を取得"""
        try:
            provider = self.holiday_factory.create(country)
            holidays = provider.get_holidays(year)
            
            if format_type == 'json':
                return {
                    'country': country,
                    'year': year,
                    'holidays': [
                        {
                            'date': h.date.isoformat(),
                            'name': h.name,
                            'category': h.category,
                            'is_substitute': h.is_substitute,
                            'weekday': h.date.strftime('%A'),
                            'description': h.description
                        }
                        for h in holidays
                    ],
                    'total_count': len(holidays),
                    'generated_at': datetime.now().isoformat()
                }
            else:
                # 他の形式での出力
                content = self.formatter_registry.format_holidays(holidays, format_type)
                return content
                
        except Exception as e:
            return {'error': str(e)}, 400
    
    def check_holiday(self, country: str, date_str: str):
        """祝日判定"""
        try:
            provider = self.holiday_factory.create(country)
            check_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            is_holiday = provider.is_holiday(check_date)
            holiday_name = None
            
            if is_holiday:
                year_holidays = provider.get_holidays(check_date.year)
                for holiday in year_holidays:
                    if holiday.date == check_date:
                        holiday_name = holiday.name
                        break
            
            return {
                'country': country,
                'date': date_str,
                'is_holiday': is_holiday,
                'holiday_name': holiday_name,
                'weekday': check_date.strftime('%A')
            }
            
        except Exception as e:
            return {'error': str(e)}, 400

# APIインスタンス
holiday_api = HolidayAPI()

@app.route('/api/countries', methods=['GET'])
def list_countries():
    """サポートされている国のリスト"""
    return jsonify({
        'countries': HolidayProviderFactory.list_countries(),
        'formats': FormatterRegistry.list_formats()
    })

@app.route('/api/holidays/<country>/<int:year>', methods=['GET'])
def get_holidays(country, year):
    """祝日一覧を取得"""
    format_type = request.args.get('format', 'json')
    
    result = holiday_api.get_holidays(country, year, format_type)
    
    if format_type == 'json':
        return jsonify(result)
    else:
        # ファイルとして返す
        formatter = FormatterRegistry.get_formatter(format_type)
        
        if isinstance(result, bytes):
            return send_file(
                io.BytesIO(result),
                mimetype=formatter.get_content_type(),
                as_attachment=True,
                download_name=f'holidays_{country}_{year}.{formatter.get_file_extension()}'
            )
        else:
            return result, 200, {'Content-Type': formatter.get_content_type()}

@app.route('/api/check/<country>/<date_str>', methods=['GET'])
def check_holiday(country, date_str):
    """祝日判定"""
    result = holiday_api.check_holiday(country, date_str)
    return jsonify(result)

@app.route('/api/holidays/<country>/range', methods=['GET'])
def get_holidays_range(country):
    """期間指定での祝日取得"""
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    
    if not start_date or not end_date:
        return jsonify({'error': 'start and end parameters are required'}), 400
    
    try:
        provider = HolidayProviderFactory.create(country)
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # 年ごとに祝日を取得
        all_holidays = []
        for year in range(start.year, end.year + 1):
            year_holidays = provider.get_holidays(year)
            for holiday in year_holidays:
                if start <= holiday.date <= end:
                    all_holidays.append(holiday)
        
        return jsonify({
            'country': country,
            'start_date': start_date,
            'end_date': end_date,
            'holidays': [
                {
                    'date': h.date.isoformat(),
                    'name': h.name,
                    'category': h.category,
                    'is_substitute': h.is_substitute
                }
                for h in all_holidays
            ],
            'total_count': len(all_holidays)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

### FastAPI ベースの高性能 API

```python
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import tempfile
import os

app = FastAPI(
    title="Holiday Calendar API",
    description="祝日カレンダー管理API",
    version="1.0.0"
)

class HolidayResponse(BaseModel):
    date: str
    name: str
    category: str
    is_substitute: bool
    weekday: str
    description: Optional[str] = None

class HolidayListResponse(BaseModel):
    country: str
    year: int
    holidays: List[HolidayResponse]
    total_count: int
    generated_at: str

class HolidayCheckResponse(BaseModel):
    country: str
    date: str
    is_holiday: bool
    holiday_name: Optional[str] = None
    weekday: str

@app.get("/countries", response_model=dict)
async def list_countries():
    """サポートされている国のリスト"""
    return {
        'countries': HolidayProviderFactory.list_countries(),
        'formats': FormatterRegistry.list_formats()
    }

@app.get("/holidays/{country}/{year}", response_model=HolidayListResponse)
async def get_holidays(
    country: str, 
    year: int,
    format: str = Query('json', description="出力形式")
):
    """祝日一覧を取得"""
    try:
        provider = HolidayProviderFactory.create(country)
        holidays = provider.get_holidays(year)
        
        if format == 'json':
            return HolidayListResponse(
                country=country,
                year=year,
                holidays=[
                    HolidayResponse(
                        date=h.date.isoformat(),
                        name=h.name,
                        category=h.category,
                        is_substitute=h.is_substitute,
                        weekday=h.date.strftime('%A'),
                        description=h.description
                    )
                    for h in holidays
                ],
                total_count=len(holidays),
                generated_at=datetime.now().isoformat()
            )
        else:
            # ファイル形式での出力
            formatter = FormatterRegistry.get_formatter(format)
            content = formatter.format_holidays(holidays)
            
            # 一時ファイルに保存
            with tempfile.NamedTemporaryFile(
                delete=False, 
                suffix=f'.{formatter.get_file_extension()}'
            ) as tmp_file:
                if isinstance(content, bytes):
                    tmp_file.write(content)
                else:
                    tmp_file.write(content.encode('utf-8'))
                tmp_file_path = tmp_file.name
            
            return FileResponse(
                tmp_file_path,
                media_type=formatter.get_content_type(),
                filename=f'holidays_{country}_{year}.{formatter.get_file_extension()}'
            )
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/check/{country}/{date_str}", response_model=HolidayCheckResponse)
async def check_holiday(country: str, date_str: str):
    """祝日判定"""
    try:
        provider = HolidayProviderFactory.create(country)
        check_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        is_holiday = provider.is_holiday(check_date)
        holiday_name = None
        
        if is_holiday:
            year_holidays = provider.get_holidays(check_date.year)
            for holiday in year_holidays:
                if holiday.date == check_date:
                    holiday_name = holiday.name
                    break
        
        return HolidayCheckResponse(
            country=country,
            date=date_str,
            is_holiday=is_holiday,
            holiday_name=holiday_name,
            weekday=check_date.strftime('%A')
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# WebSocket サポート（リアルタイム更新）
from fastapi import WebSocket

@app.websocket("/ws/holidays/{country}")
async def websocket_holidays(websocket: WebSocket, country: str):
    """WebSocket経由でのリアルタイム祝日情報"""
    await websocket.accept()
    
    try:
        provider = HolidayProviderFactory.create(country)
        
        while True:
            # クライアントからのメッセージを待機
            data = await websocket.receive_json()
            
            if data.get('action') == 'get_holidays':
                year = data.get('year', datetime.now().year)
                holidays = provider.get_holidays(year)
                
                response = {
                    'action': 'holidays_data',
                    'country': country,
                    'year': year,
                    'holidays': [
                        {
                            'date': h.date.isoformat(),
                            'name': h.name,
                            'category': h.category
                        }
                        for h in holidays
                    ]
                }
                
                await websocket.send_json(response)
                
            elif data.get('action') == 'check_holiday':
                date_str = data.get('date')
                check_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                is_holiday = provider.is_holiday(check_date)
                
                response = {
                    'action': 'holiday_check_result',
                    'date': date_str,
                    'is_holiday': is_holiday
                }
                
                await websocket.send_json(response)
                
    except Exception as e:
        await websocket.send_json({'error': str(e)})
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

このカスタマイズ・拡張ガイドにより、開発者は様々な要件に応じてツールを柔軟に拡張できます。