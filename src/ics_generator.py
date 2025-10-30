"""ICS file generation module.

要件2の実装: AWS SSM Change Calendar用ICS変換
- AWS SSM仕様準拠（PRODID: -//AWS//Change Calendar 1.0//EN）
- 当年以降データ変換
- 文字エンコーディング（UTF-8）
- イベントプロパティ（UID、DTSTAMP、SUMMARY、DTSTART、DTEND）
- AWS SSM互換性保証
"""

from icalendar import Calendar, Event, Timezone, TimezoneStandard
from datetime import datetime, timezone, date, timedelta
from typing import Dict, List, Optional, Tuple
import json
import pytz
import logging
from .japanese_holidays import JapaneseHolidays
from .security import SecureFileHandler, validate_file_path_input
from .error_handler import ValidationError

# カスタム例外クラス
class ICSGenerationError(Exception):
    """ICS生成関連エラー"""
    pass

class AWSSSMFormatError(ICSGenerationError):
    """AWS SSM形式エラー"""
    pass

class EncodingError(ICSGenerationError):
    """エンコーディングエラー"""
    pass


class ICSGenerator:
    """Generate ICS files from AWS Change Calendar data."""
    
    def __init__(self, japanese_holidays: Optional[JapaneseHolidays] = None, exclude_sunday_holidays: bool = True):
        """AWS SSM Change Calendar用ICSジェネレーター初期化.
        
        要件2: AWS SSM Change Calendar用ICS変換
        
        Args:
            japanese_holidays: JapaneseHolidaysインスタンス
            exclude_sunday_holidays: 日曜祝日を除外するかどうか（デフォルト: True）
        """
        self.calendar = None
        self.japanese_holidays = japanese_holidays or JapaneseHolidays()
        self.logger = logging.getLogger(__name__)
        self.tokyo_tz = pytz.timezone('Asia/Tokyo')
        self._events_converted = False  # イベント変換済みフラグ
        self.exclude_sunday_holidays = exclude_sunday_holidays  # 日曜祝日除外フラグ
        
        # AWS SSM Change Calendar専用カレンダー作成
        self.create_aws_ssm_calendar()
    
    def create_aws_ssm_calendar(self) -> None:
        """AWS SSM Change Calendar専用カレンダー作成.
        
        要件2: AWS SSM仕様準拠
        """
        try:
            self.calendar = Calendar()
            
            # AWS SSM Change Calendar必須プロパティ
            self.calendar.add('prodid', '-//AWS//Change Calendar 1.0//EN')
            self.calendar.add('version', '2.0')
            
            # AWS SSM Change Calendar専用プロパティ
            self.calendar.add('X-CALENDAR-TYPE', 'DEFAULT_OPEN')
            self.calendar.add('X-WR-CALDESC', '')
            self.calendar.add('X-CALENDAR-CMEVENTS', 'DISABLED')
            self.calendar.add('X-WR-TIMEZONE', 'Asia/Tokyo')
            
            # Asia/Tokyoタイムゾーン定義追加
            self.add_timezone_definition()
            
            self.logger.info("AWS SSM Change Calendar専用カレンダー作成完了")
            
        except Exception as e:
            raise AWSSSMFormatError(f"AWS SSM Change Calendarカレンダー作成失敗: {e}")
    
    def add_timezone_definition(self) -> None:
        """Asia/Tokyoタイムゾーン定義追加.
        
        要件2: AWS SSM互換性保証
        """
        try:
            tz_component = Timezone()
            tz_component.add('tzid', 'Asia/Tokyo')
            
            # 標準時間コンポーネント追加
            tz_standard = TimezoneStandard()
            tz_standard.add('dtstart', datetime(1970, 1, 1))
            tz_standard.add('tzoffsetfrom', timedelta(hours=9))  # +09:00
            tz_standard.add('tzoffsetto', timedelta(hours=9))    # +09:00
            tz_standard.add('tzname', 'JST')
            
            tz_component.add_component(tz_standard)
            self.calendar.add_component(tz_component)
            
            self.logger.info("Asia/Tokyoタイムゾーン定義追加完了")
            
        except Exception as e:
            raise AWSSSMFormatError(f"タイムゾーン定義追加失敗: {e}")
    
    def validate_aws_ssm_compatibility(self) -> bool:
        """AWS SSM Change Calendar互換性検証.
        
        要件2: AWS SSM互換性保証
        
        Returns:
            True if compatible with AWS SSM Change Calendar
        """
        try:
            # 必須プロパティ確認
            required_props = ['prodid', 'version']
            for prop in required_props:
                if prop not in self.calendar:
                    self.logger.error(f"必須プロパティ不足: {prop}")
                    return False
            
            # PRODID確認
            prodid = str(self.calendar['prodid'])
            if prodid != '-//AWS//Change Calendar 1.0//EN':
                self.logger.error(f"不正なPRODID: {prodid}")
                return False
            
            # タイムゾーン定義確認
            has_timezone = any(
                component.name == 'VTIMEZONE' 
                for component in self.calendar.subcomponents
            )
            if not has_timezone:
                self.logger.error("VTIMEZONEコンポーネントが不足")
                return False
            
            self.logger.info("AWS SSM Change Calendar互換性検証完了")
            return True
            
        except Exception as e:
            self.logger.error(f"互換性検証エラー: {e}")
            return False
    
    def generate_ics_content(self) -> str:
        """AWS SSM互換ICS形式文字列生成.
        
        要件2: 文字エンコーディング（UTF-8）、AWS SSM互換性
        
        Returns:
            UTF-8エンコードされたICS文字列
            
        Raises:
            EncodingError: エンコーディングエラー
        """
        try:
            # 祝日イベントを変換
            self.convert_holidays_to_events()
            
            # ICS形式に変換
            ics_bytes = self.calendar.to_ical()
            
            # UTF-8デコード
            ics_content = ics_bytes.decode('utf-8')
            
            # AWS SSM互換性のためのクリーニング
            ics_content = self._clean_ics_content(ics_content)
            
            self.logger.info("AWS SSM互換ICS形式文字列生成完了")
            return ics_content
            
        except UnicodeDecodeError as e:
            raise EncodingError(f"UTF-8デコードエラー: {e}")
        except Exception as e:
            raise ICSGenerationError(f"ICS形式文字列生成失敗: {e}")
    
    def _clean_ics_content(self, content: str) -> str:
        """Clean ICS content by removing unwanted escape sequences.
        
        Args:
            content: Raw ICS content
            
        Returns:
            Cleaned ICS content
        """
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Remove \n at the end of SUMMARY and DESCRIPTION lines
            if line.startswith('SUMMARY:') and '\\n' in line:
                line = line.replace('\\n', '')
            elif line.startswith('DESCRIPTION:') and '\\n' in line:
                line = line.replace('\\n', '')
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def save_to_file(self, filepath: str) -> None:
        """UTF-8エンコーディングでファイル保存.
        
        要件2: 文字エンコーディング（UTF-8）
        
        Args:
            filepath: 出力ファイルパス
            
        Raises:
            ICSGenerationError: ファイル保存エラー
            ValidationError: ファイルパス検証エラー
        """
        try:
            # ファイルパスのセキュリティ検証
            validated_path = validate_file_path_input(filepath, allow_create=True)
            
            # AWS SSM互換ICS内容生成
            ics_content = self.generate_ics_content()
            
            # セキュアファイルハンドラーでUTF-8エンコーディング保存
            SecureFileHandler.write_secure_file(
                validated_path, 
                ics_content, 
                permissions=SecureFileHandler.READABLE_FILE_PERMISSIONS
            )
            
            self.logger.info(f"ICSファイル保存完了: {validated_path}")
            
        except (EncodingError, ICSGenerationError, ValidationError):
            # 既知のエラーは再発生
            raise
        except Exception as e:
            # フォールバック保存を試行
            try:
                self.logger.warning(f"通常保存失敗、フォールバック保存を試行: {e}")
                validated_path = validate_file_path_input(filepath, allow_create=True)
                ics_bytes = self.calendar.to_ical()
                
                # バイナリデータをUTF-8文字列に変換してセキュア保存
                ics_content = ics_bytes.decode('utf-8')
                SecureFileHandler.write_secure_file(
                    validated_path, 
                    ics_content, 
                    permissions=SecureFileHandler.READABLE_FILE_PERMISSIONS
                )
                self.logger.info(f"フォールバック保存完了: {validated_path}")
            except Exception as e2:
                raise ICSGenerationError(f"ファイル保存失敗（フォールバックも失敗）: {e2}")
    
    def filter_sunday_holidays(self, holidays: List[Tuple[date, str]]) -> Tuple[List[Tuple[date, str]], List[Tuple[date, str]]]:
        """日曜祝日のフィルタリング.
        
        要件2拡張: 日曜祝日除外機能
        
        Args:
            holidays: 祝日データリスト
            
        Returns:
            (フィルタ後祝日リスト, 除外された日曜祝日リスト)
        """
        try:
            filtered_holidays = []
            sunday_holidays = []
            
            for holiday_date, holiday_name in holidays:
                # 日曜日は weekday() == 6
                if holiday_date.weekday() == 6:
                    sunday_holidays.append((holiday_date, holiday_name))
                    if not self.exclude_sunday_holidays:
                        # 日曜祝日を維持する場合は含める
                        filtered_holidays.append((holiday_date, holiday_name))
                else:
                    filtered_holidays.append((holiday_date, holiday_name))
            
            if self.exclude_sunday_holidays and sunday_holidays:
                self.logger.info(f"日曜祝日除外: {len(sunday_holidays)} 件")
                for holiday_date, holiday_name in sunday_holidays:
                    self.logger.info(f"  除外: {holiday_date.strftime('%Y/%m/%d')} ({holiday_date.strftime('%A')}) - {holiday_name}")
            elif sunday_holidays:
                self.logger.info(f"日曜祝日維持: {len(sunday_holidays)} 件")
            
            return filtered_holidays, sunday_holidays
            
        except Exception as e:
            raise ICSGenerationError(f"日曜祝日フィルタリング失敗: {e}")
    
    def convert_current_year_onwards_holidays(self) -> List[Tuple[date, str]]:
        """当年以降の祝日データを取得.
        
        要件2: 当年以降データ変換
        
        Returns:
            当年以降の祝日データリスト（日曜祝日フィルタリング適用済み）
        """
        try:
            current_year = datetime.now().year
            start_date = date(current_year, 1, 1)
            
            # 将来の祝日も含めて取得（例：2030年まで）
            end_date = date(current_year + 5, 12, 31)
            
            all_holidays = self.japanese_holidays.get_holidays_in_range(start_date, end_date)
            self.logger.info(f"当年以降祝日データ取得: {len(all_holidays)} 件")
            
            # 日曜祝日フィルタリング適用
            filtered_holidays, sunday_holidays = self.filter_sunday_holidays(all_holidays)
            
            self.logger.info(f"フィルタリング後祝日データ: {len(filtered_holidays)} 件")
            
            return filtered_holidays
            
        except Exception as e:
            raise ICSGenerationError(f"当年以降祝日データ取得失敗: {e}")
    
    def generate_holiday_event(self, holiday_date: date, holiday_name: str) -> Event:
        """個別祝日イベント生成.
        
        要件2: イベントプロパティ（UID、DTSTAMP、SUMMARY、DTSTART、DTEND）
        
        Args:
            holiday_date: 祝日の日付
            holiday_name: 祝日名
            
        Returns:
            生成されたイベント
        """
        try:
            event = Event()
            
            # 祝日名のクリーニング
            clean_holiday_name = holiday_name.strip()
            
            # 必須プロパティ設定
            event.add('summary', f'日本の祝日: {clean_holiday_name}')
            event.add('description', f'日本の国民の祝日: {clean_holiday_name}')
            event.add('categories', 'Japanese-Holiday')
            
            # 終日イベント設定（翌日00:00まで）
            next_day = holiday_date + timedelta(days=1)
            
            # Asia/Tokyoタイムゾーンでの日時設定
            start_datetime = self.tokyo_tz.localize(
                datetime.combine(holiday_date, datetime.min.time())
            )
            end_datetime = self.tokyo_tz.localize(
                datetime.combine(next_day, datetime.min.time())
            )
            
            event.add('dtstart', start_datetime)
            event.add('dtend', end_datetime)
            event.add('dtstamp', datetime.now(timezone.utc))
            
            # AWS SSM Change Calendar互換のUID生成
            uid = f"jp-holiday-{holiday_date.strftime('%Y%m%d')}@aws-ssm-change-calendar"
            event.add('uid', uid)
            
            # タイムゾーンパラメータ設定
            event['dtstart'].params['TZID'] = 'Asia/Tokyo'
            event['dtend'].params['TZID'] = 'Asia/Tokyo'
            
            return event
            
        except Exception as e:
            raise ICSGenerationError(f"祝日イベント生成失敗 ({holiday_date}): {e}")
    
    def add_japanese_holidays_for_year(self, year: int) -> None:
        """指定年の日本の祝日をカレンダーに追加.
        
        Args:
            year: 対象年
            
        Raises:
            ICSGenerationError: 祝日追加エラー
        """
        try:
            # 指定年の祝日を取得
            start_date = date(year, 1, 1)
            end_date = date(year, 12, 31)
            
            holidays = self.japanese_holidays.get_holidays_in_range(start_date, end_date)
            
            # 日曜祝日フィルタリング適用
            filtered_holidays, sunday_holidays = self.filter_sunday_holidays(holidays)
            
            # 各祝日をイベントに変換してカレンダーに追加
            for holiday_date, holiday_name in filtered_holidays:
                event = self.generate_holiday_event(holiday_date, holiday_name)
                self.calendar.add_component(event)
            
            self.logger.info(f"{year}年の祝日追加完了: {len(filtered_holidays)} 件")
            
            if self.exclude_sunday_holidays and sunday_holidays:
                self.logger.info(f"日曜祝日除外: {len(sunday_holidays)} 件")
            
        except Exception as e:
            raise ICSGenerationError(f"{year}年の祝日追加失敗: {e}")
    
    def add_japanese_holidays(self, start_date: date, end_date: date) -> None:
        """指定期間の日本の祝日をカレンダーに追加.
        
        Args:
            start_date: 開始日
            end_date: 終了日
            
        Raises:
            ICSGenerationError: 祝日追加エラー
        """
        try:
            holidays = self.japanese_holidays.get_holidays_in_range(start_date, end_date)
            
            # 日曜祝日フィルタリング適用
            filtered_holidays, sunday_holidays = self.filter_sunday_holidays(holidays)
            
            # 各祝日をイベントに変換してカレンダーに追加
            for holiday_date, holiday_name in filtered_holidays:
                event = self.generate_holiday_event(holiday_date, holiday_name)
                self.calendar.add_component(event)
            
            self.logger.info(f"期間 {start_date} - {end_date} の祝日追加完了: {len(filtered_holidays)} 件")
            
            if self.exclude_sunday_holidays and sunday_holidays:
                self.logger.info(f"日曜祝日除外: {len(sunday_holidays)} 件")
            
        except Exception as e:
            raise ICSGenerationError(f"期間 {start_date} - {end_date} の祝日追加失敗: {e}")

    def clear_events(self) -> None:
        """カレンダーからすべてのイベントをクリア."""
        try:
            # VEVENTコンポーネントのみを削除
            components_to_remove = []
            for component in self.calendar.subcomponents:
                if component.name == 'VEVENT':
                    components_to_remove.append(component)
            
            for component in components_to_remove:
                self.calendar.subcomponents.remove(component)
            
            # 変換済みフラグをリセット
            self._events_converted = False
            
            self.logger.info("イベントクリア完了")
            
        except Exception as e:
            raise ICSGenerationError(f"イベントクリア失敗: {e}")

    def convert_holidays_to_events(self) -> None:
        """祝日データをICSイベントに変換.
        
        要件2: 当年以降データ変換
        """
        try:
            # 既に変換済みの場合はスキップ
            if self._events_converted:
                self.logger.info("祝日イベントは既に変換済みです")
                return
            
            # 当年以降の祝日データ取得
            holidays = self.convert_current_year_onwards_holidays()
            
            # 各祝日をイベントに変換
            for holiday_date, holiday_name in holidays:
                event = self.generate_holiday_event(holiday_date, holiday_name)
                self.calendar.add_component(event)
            
            # 変換済みフラグを設定
            self._events_converted = True
            
            self.logger.info(f"祝日イベント変換完了: {len(holidays)} 件")
            
        except Exception as e:
            raise ICSGenerationError(f"祝日イベント変換失敗: {e}")
    
    def get_generation_stats(self) -> Dict:
        """ICS生成統計情報取得.
        
        Returns:
            生成統計情報
        """
        try:
            events = [
                component for component in self.calendar.subcomponents
                if component.name == 'VEVENT'
            ]
            
            holiday_events = [
                event for event in events
                if 'Japanese-Holiday' in str(event.get('categories', ''))
            ]
            
            # 日曜祝日統計を取得
            current_year = datetime.now().year
            start_date = date(current_year, 1, 1)
            end_date = date(current_year + 5, 12, 31)
            all_holidays = self.japanese_holidays.get_holidays_in_range(start_date, end_date)
            _, sunday_holidays = self.filter_sunday_holidays(all_holidays)
            
            return {
                'total_events': len(events),
                'holiday_events': len(holiday_events),
                'has_timezone': any(
                    component.name == 'VTIMEZONE' 
                    for component in self.calendar.subcomponents
                ),
                'aws_ssm_compatible': self.validate_aws_ssm_compatibility(),
                'exclude_sunday_holidays': self.exclude_sunday_holidays,
                'sunday_holidays_found': len(sunday_holidays),
                'sunday_holidays_excluded': len(sunday_holidays) if self.exclude_sunday_holidays else 0
            }
            
        except Exception as e:
            self.logger.error(f"統計情報取得エラー: {e}")
            return {'error': str(e)}