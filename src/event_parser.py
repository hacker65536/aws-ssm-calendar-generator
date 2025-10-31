"""Event list parser and ICS extender module.

要件5の実装: 簡易イベントリストからのICS拡張機能
- 簡易イベントファイル解析（タブ区切り・スペース区切り・カンマ区切り）
- 柔軟な日時形式対応（ISO8601、日付のみ）
- 終日イベント自動判定
- 既存ICS拡張機能
- 重複回避機能
"""

import csv
import re
import hashlib
from datetime import datetime, date, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path
import logging
import pytz
from icalendar import Calendar, Event

from .error_handler import (
    BaseApplicationError, ValidationError, ErrorCategory, ErrorSeverity,
    with_error_handling, handle_error
)
from .security import validate_file_path_input
from .datetime_handler import DateTimeHandler


class EventParsingError(BaseApplicationError):
    """イベント解析エラー"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.DATA,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class ICSExtensionError(BaseApplicationError):
    """ICS拡張エラー"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.FILE_SYSTEM,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class DuplicateEventError(BaseApplicationError):
    """重複イベントエラー"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.DATA,
            severity=ErrorSeverity.LOW,
            **kwargs
        )


class EventListParser:
    """簡易イベントリストファイルのパーサー"""
    
    # サポートする区切り文字（優先順位順）
    SUPPORTED_DELIMITERS = {
        'tab': {
            'delimiter': '\t',
            'priority': 1,
            'name': 'タブ区切り',
            'example': 'イベント名\t開始日時\t終了日時'
        },
        'space': {
            'delimiter': ' ',
            'priority': 2,
            'name': 'スペース区切り',
            'example': 'イベント名 開始日時 終了日時'
        },
        'comma': {
            'delimiter': ',',
            'priority': 3,
            'name': 'カンマ区切り',
            'example': 'イベント名,開始日時,終了日時'
        }
    }
    
    # 日時形式パターン
    DATETIME_PATTERNS = [
        # ISO8601形式
        (r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$', '%Y-%m-%dT%H:%M:%S'),
        (r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$', '%Y-%m-%d %H:%M:%S'),
        (r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$', '%Y-%m-%dT%H:%M'),
        (r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$', '%Y-%m-%d %H:%M'),
        # 日付のみ（終日イベント）
        (r'^\d{4}-\d{2}-\d{2}$', '%Y-%m-%d'),
        # スラッシュ区切り
        (r'^\d{4}/\d{2}/\d{2}T\d{2}:\d{2}:\d{2}$', '%Y/%m/%dT%H:%M:%S'),
        (r'^\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}$', '%Y/%m/%d %H:%M:%S'),
        (r'^\d{4}/\d{2}/\d{2}$', '%Y/%m/%d'),
    ]
    
    def __init__(self):
        """EventListParser初期化"""
        self.logger = logging.getLogger(__name__)
        self.tokyo_tz = pytz.timezone('Asia/Tokyo')
        self.datetime_handler = DateTimeHandler('Asia/Tokyo')
    
    @with_error_handling(operation_name="parse_event_file", category=ErrorCategory.DATA)
    def parse_event_file(self, filepath: str) -> List[Dict]:
        """イベントファイル解析
        
        Args:
            filepath: イベントファイルのパス
            
        Returns:
            解析されたイベントデータのリスト
            
        Raises:
            EventParsingError: 解析エラー
        """
        try:
            # ファイルパス検証
            validated_path = validate_file_path_input(filepath, require_exists=True)
            
            # ファイル読み込み
            content = self._read_file_with_encoding(str(validated_path))
            
            # 区切り文字検出
            delimiter = self.detect_delimiter(content)
            
            # 行単位で解析
            events = []
            errors = []
            lines = content.strip().split('\n')
            header_skipped = False
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # 空行やコメント行をスキップ
                if not line or line.startswith('#'):
                    continue
                
                # ヘッダー行検出・スキップ
                if not header_skipped and self._is_header_line(line, delimiter):
                    header_skipped = True
                    self.logger.info(f"ヘッダー行をスキップ: {line}")
                    continue
                
                try:
                    event = self._parse_event_line(line, delimiter, line_num)
                    if event:
                        events.append(event)
                except Exception as e:
                    errors.append(f"行 {line_num}: {e}")
            
            if errors:
                error_msg = f"解析エラーが発生しました:\n" + "\n".join(errors)
                raise EventParsingError(error_msg)
            
            self.logger.info(f"イベント解析完了: {len(events)} 件")
            return events
            
        except EventParsingError:
            raise
        except Exception as e:
            raise EventParsingError(f"ファイル解析失敗: {e}")
    
    def detect_delimiter(self, content: str) -> str:
        """区切り文字自動検出
        
        Args:
            content: ファイル内容
            
        Returns:
            検出された区切り文字
        """
        lines = [line.strip() for line in content.split('\n') if line.strip() and not line.strip().startswith('#')]
        
        if not lines:
            return '\t'  # デフォルトはタブ
        
        # 各区切り文字での分割数をカウント
        delimiter_scores = {}
        
        for delimiter_info in self.SUPPORTED_DELIMITERS.values():
            delimiter = delimiter_info['delimiter']
            total_fields = 0
            valid_lines = 0
            
            for line in lines[:5]:  # 最初の5行で判定
                fields = line.split(delimiter)
                if len(fields) >= 2:  # 最低2フィールド必要
                    total_fields += len(fields)
                    valid_lines += 1
            
            if valid_lines > 0:
                avg_fields = total_fields / valid_lines
                # 優先度と平均フィールド数でスコア計算
                score = avg_fields * (4 - delimiter_info['priority'])
                delimiter_scores[delimiter] = score
        
        # 最高スコアの区切り文字を選択
        if delimiter_scores:
            best_delimiter = max(delimiter_scores.keys(), key=lambda k: delimiter_scores[k])
            delimiter_name = next(
                info['name'] for info in self.SUPPORTED_DELIMITERS.values() 
                if info['delimiter'] == best_delimiter
            )
            self.logger.info(f"区切り文字検出: {delimiter_name}")
            return best_delimiter
        
        return '\t'  # デフォルト
    
    def parse_datetime(self, datetime_str: str) -> Tuple[Optional[datetime], bool]:
        """日時解析と終日イベント判定
        
        Args:
            datetime_str: 日時文字列
            
        Returns:
            (解析された日時, 終日イベントフラグ)
        """
        if not datetime_str or datetime_str.strip() == '':
            return None, False
        
        datetime_str = datetime_str.strip()
        
        for pattern, format_str in self.DATETIME_PATTERNS:
            if re.match(pattern, datetime_str):
                try:
                    parsed_dt = datetime.strptime(datetime_str, format_str)
                    
                    # 時刻情報があるかチェック
                    has_time = 'T' in format_str or ' ' in format_str
                    is_all_day = not has_time
                    
                    return parsed_dt, is_all_day
                    
                except ValueError:
                    continue
        
        raise ValueError(f"サポートされていない日時形式: {datetime_str}")
    
    def validate_event_data(self, events: List[Dict]) -> List[str]:
        """イベントデータ検証
        
        Args:
            events: イベントデータリスト
            
        Returns:
            検証エラーのリスト
        """
        errors = []
        
        for i, event in enumerate(events, 1):
            # 必須フィールドチェック
            if not event.get('name'):
                errors.append(f"イベント {i}: イベント名が空です")
            
            if not event.get('start_datetime'):
                errors.append(f"イベント {i}: 開始日時が無効です")
            
            # 日時の妥当性チェック
            start_dt = event.get('start_datetime')
            end_dt = event.get('end_datetime')
            
            if start_dt and end_dt and start_dt >= end_dt:
                errors.append(f"イベント {i}: 終了日時が開始日時より前です")
            
            # 過去の日付チェック（警告レベル）
            if start_dt and start_dt.date() < date.today():
                self.logger.warning(f"イベント {i}: 過去の日付です - {event['name']}")
        
        return errors
    
    def _read_file_with_encoding(self, filepath: str) -> str:
        """エンコーディング自動検出でファイル読み込み"""
        encodings = ['utf-8', 'shift_jis', 'cp932', 'euc-jp']
        
        for encoding in encodings:
            try:
                with open(filepath, 'r', encoding=encoding) as f:
                    content = f.read()
                self.logger.info(f"ファイル読み込み成功: {encoding}")
                return content
            except UnicodeDecodeError:
                continue
        
        raise EventParsingError(f"ファイルのエンコーディングを検出できませんでした: {filepath}")
    
    def _is_header_line(self, line: str, delimiter: str) -> bool:
        """ヘッダー行判定"""
        fields = line.split(delimiter)
        
        # 典型的なヘッダー文字列
        header_keywords = [
            'イベント名', 'event', 'name', 'title',
            '開始', 'start', 'begin',
            '終了', 'end', 'finish',
            '日時', 'datetime', 'date', 'time'
        ]
        
        for field in fields:
            field_lower = field.lower().strip()
            if any(keyword in field_lower for keyword in header_keywords):
                return True
        
        return False
    
    def _parse_event_line(self, line: str, delimiter: str, line_num: int) -> Optional[Dict]:
        """イベント行解析"""
        fields = [field.strip() for field in line.split(delimiter)]
        
        if len(fields) < 2:
            raise ValueError(f"フィールド数が不足しています（最低2つ必要）: {len(fields)}")
        
        # イベント名
        event_name = fields[0]
        if not event_name:
            raise ValueError("イベント名が空です")
        
        # 開始日時
        start_datetime_str = fields[1] if len(fields) > 1 else ''
        start_datetime, start_is_all_day = self.parse_datetime(start_datetime_str)
        
        if not start_datetime:
            raise ValueError(f"開始日時が無効です: {start_datetime_str}")
        
        # 終了日時（オプション）
        end_datetime = None
        end_is_all_day = start_is_all_day
        
        if len(fields) > 2 and fields[2]:
            end_datetime_str = fields[2]
            end_datetime, end_is_all_day = self.parse_datetime(end_datetime_str)
        
        # 終日イベント判定
        is_all_day = start_is_all_day or (end_datetime is None)
        
        # 終了日時が未指定の場合の処理
        if not end_datetime:
            if is_all_day:
                # 終日イベントの場合は翌日
                end_datetime = start_datetime + timedelta(days=1)
            else:
                # 時刻指定イベントの場合は1時間後
                end_datetime = start_datetime + timedelta(hours=1)
        
        return {
            'name': event_name,
            'start_datetime': start_datetime,
            'end_datetime': end_datetime,
            'is_all_day': is_all_day,
            'line_number': line_num
        }


class ICSExtender:
    """既存ICSファイルへのイベント追加機能"""
    
    def __init__(self, base_ics_path: str):
        """ICS拡張器初期化
        
        Args:
            base_ics_path: ベースとなるICSファイルのパス
        """
        self.base_ics_path = validate_file_path_input(base_ics_path, require_exists=True)
        self.logger = logging.getLogger(__name__)
        self.tokyo_tz = pytz.timezone('Asia/Tokyo')
        self.calendar = None
        self.existing_events = []
    
    @with_error_handling(operation_name="load_existing_ics", category=ErrorCategory.FILE_SYSTEM)
    def load_existing_ics(self) -> Calendar:
        """既存ICSファイル読み込み
        
        Returns:
            読み込まれたCalendarオブジェクト
            
        Raises:
            ICSExtensionError: 読み込みエラー
        """
        try:
            with open(self.base_ics_path, 'rb') as f:
                self.calendar = Calendar.from_ical(f.read())
            
            # 既存イベントを抽出
            self.existing_events = []
            for component in self.calendar.walk():
                if component.name == 'VEVENT':
                    self.existing_events.append(component)
            
            self.logger.info(f"既存ICS読み込み完了: {len(self.existing_events)} イベント")
            return self.calendar
            
        except Exception as e:
            raise ICSExtensionError(f"ICSファイル読み込み失敗: {e}")
    
    def add_custom_events(self, events: List[Dict], skip_duplicates: bool = True) -> int:
        """カスタムイベント追加
        
        Args:
            events: 追加するイベントデータのリスト
            skip_duplicates: 重複イベントをスキップするか
            
        Returns:
            実際に追加されたイベント数
            
        Raises:
            ICSExtensionError: 追加エラー
        """
        if not self.calendar:
            self.load_existing_ics()
        
        added_count = 0
        skipped_count = 0
        
        for event_data in events:
            try:
                # 重複チェック
                if skip_duplicates and self.detect_duplicates(event_data):
                    skipped_count += 1
                    self.logger.info(f"重複イベントをスキップ: {event_data['name']}")
                    continue
                
                # カスタムイベント生成
                ics_event = self.generate_custom_event(event_data)
                self.calendar.add_component(ics_event)
                added_count += 1
                
            except Exception as e:
                self.logger.error(f"イベント追加失敗: {event_data.get('name', 'Unknown')} - {e}")
                raise ICSExtensionError(f"イベント追加失敗: {e}")
        
        self.logger.info(f"カスタムイベント追加完了: {added_count} 件追加, {skipped_count} 件スキップ")
        return added_count
    
    def detect_duplicates(self, new_event: Dict) -> bool:
        """重複イベント検出
        
        Args:
            new_event: 新しいイベントデータ
            
        Returns:
            重複している場合True
        """
        new_start = new_event['start_datetime']
        new_name = new_event['name'].lower().strip()
        
        for existing_event in self.existing_events:
            # 開始日時比較
            existing_start = existing_event.get('dtstart')
            if not existing_start:
                continue
            
            # 日時正規化
            if hasattr(existing_start.dt, 'date'):
                existing_start_dt = existing_start.dt
            else:
                existing_start_dt = datetime.combine(existing_start.dt, datetime.min.time())
            
            # 同一日付チェック
            if new_start.date() == existing_start_dt.date():
                # イベント名比較
                existing_summary = str(existing_event.get('summary', '')).lower().strip()
                
                # 部分一致または完全一致
                if (new_name in existing_summary or 
                    existing_summary in new_name or 
                    new_name == existing_summary):
                    return True
        
        return False
    
    def generate_custom_event(self, event_data: Dict) -> Event:
        """カスタムイベント生成
        
        Args:
            event_data: イベントデータ
            
        Returns:
            生成されたEventオブジェクト
        """
        event = Event()
        
        # 基本プロパティ
        event.add('summary', f"カスタムイベント: {event_data['name']}")
        event.add('description', f"カスタムイベント: {event_data['name']}")
        event.add('categories', 'Custom-Event')
        
        # 日時設定
        if event_data['is_all_day']:
            # 終日イベント
            event.add('dtstart', event_data['start_datetime'].date())
            event.add('dtend', event_data['end_datetime'].date())
        else:
            # 時刻指定イベント
            start_dt = self.tokyo_tz.localize(event_data['start_datetime'])
            end_dt = self.tokyo_tz.localize(event_data['end_datetime'])
            
            event.add('dtstart', start_dt)
            event.add('dtend', end_dt)
            event['dtstart'].params['TZID'] = 'Asia/Tokyo'
            event['dtend'].params['TZID'] = 'Asia/Tokyo'
        
        # UID生成
        uid_source = f"{event_data['name']}-{event_data['start_datetime'].isoformat()}"
        uid_hash = hashlib.md5(uid_source.encode('utf-8')).hexdigest()[:8]
        event.add('uid', f"custom-event-{uid_hash}@aws-ssm-change-calendar")
        
        # タイムスタンプ
        event.add('dtstamp', datetime.now(timezone.utc))
        
        return event
    
    @with_error_handling(operation_name="save_extended_ics", category=ErrorCategory.FILE_SYSTEM)
    def save_extended_ics(self, output_path: str) -> None:
        """拡張ICSファイル保存
        
        Args:
            output_path: 出力ファイルパス
            
        Raises:
            ICSExtensionError: 保存エラー
        """
        try:
            validated_path = validate_file_path_input(output_path, allow_create=True)
            
            # ICS内容生成
            ics_content = self.calendar.to_ical()
            
            # ファイル保存
            with open(validated_path, 'wb') as f:
                f.write(ics_content)
            
            self.logger.info(f"拡張ICSファイル保存完了: {validated_path}")
            
        except Exception as e:
            raise ICSExtensionError(f"ICSファイル保存失敗: {e}")