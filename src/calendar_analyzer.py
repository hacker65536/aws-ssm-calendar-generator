"""ICS file analysis module.

要件3の実装: ICSファイル解析・可視化
- ICS解析機能: ICSファイルを構造化データとして解析
- 人間可読形式出力: 日付順ソート、表形式表示
- 統計情報表示: 総イベント数、対象期間、祝日種類別集計
- エラー検出: 構文エラー、不正データの検出・報告
- 複数形式対応: 標準出力、JSON、CSV形式での出力
"""

import re
import json
import csv
import io
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from collections import Counter, defaultdict
from pathlib import Path
import calendar as cal
import logging
from icalendar import Calendar, Event

# カスタム例外クラス
class ICSAnalysisError(Exception):
    """ICS解析関連エラー"""
    pass

class ICSFormatError(ICSAnalysisError):
    """ICS形式エラー"""
    pass

class ICSValidationError(ICSAnalysisError):
    """ICS検証エラー"""
    pass


class ICSAnalyzer:
    """Analyze AWS Change Calendar content and provide insights."""
    
    def __init__(self):
        """ICSファイル解析器初期化.
        
        要件3: ICSファイル解析・可視化
        """
        self.logger = logging.getLogger(__name__)
        self.analysis_result = None
    
    def parse_ics_file(self, filepath: str) -> Dict:
        """ICSファイル解析.
        
        要件3: ICS解析機能
        
        Args:
            filepath: ICSファイルパス
            
        Returns:
            解析結果辞書
            
        Raises:
            ICSAnalysisError: 解析エラー
        """
        try:
            # ファイル存在確認
            if not Path(filepath).exists():
                raise ICSAnalysisError(f"ファイルが存在しません: {filepath}")
            
            # ファイル読み込み
            with open(filepath, 'r', encoding='utf-8') as f:
                ics_content = f.read()
            
            # icalendarライブラリでパース
            calendar = Calendar.from_ical(ics_content)
            
            # イベント抽出
            events = self.extract_events(calendar)
            
            # 解析実行
            analysis = self.analyze_events(events)
            
            # ファイル情報追加
            file_info = {
                'filepath': filepath,
                'file_size': len(ics_content.encode('utf-8')),
                'total_events': len(events),
                'analysis_date': datetime.now().isoformat()
            }
            
            # 検証実行
            validation_errors = self.validate_ics_format(calendar)
            
            # 結果統合
            self.analysis_result = {
                'file_info': file_info,
                'events': events,
                'statistics': analysis,
                'validation_errors': validation_errors
            }
            
            self.logger.info(f"ICSファイル解析完了: {filepath} ({len(events)} イベント)")
            
            return self.analysis_result
            
        except Exception as e:
            if isinstance(e, ICSAnalysisError):
                raise
            else:
                raise ICSAnalysisError(f"ICSファイル解析失敗: {e}")
    
    def extract_events(self, calendar: Calendar) -> List[Dict]:
        """イベント情報抽出.
        
        要件3: ICS解析機能
        
        Args:
            calendar: icalendarオブジェクト
            
        Returns:
            抽出されたイベントリスト
        """
        try:
            events = []
            
            for component in calendar.walk():
                if component.name == "VEVENT":
                    event_data = {
                        'uid': str(component.get('uid', '')),
                        'summary': str(component.get('summary', '')),
                        'description': str(component.get('description', '')),
                        'categories': str(component.get('categories', '')) if component.get('categories') else '',
                        'dtstart': None,
                        'dtend': None,
                        'dtstamp': None
                    }
                    
                    # カテゴリの適切な文字列変換
                    if 'categories' in component:
                        categories = component['categories']
                        if hasattr(categories, 'to_ical'):
                            event_data['categories'] = categories.to_ical().decode('utf-8')
                        else:
                            event_data['categories'] = str(categories)
                    
                    # 日時情報の処理
                    for dt_field in ['dtstart', 'dtend', 'dtstamp']:
                        if dt_field in component:
                            dt_value = component[dt_field].dt
                            if isinstance(dt_value, datetime):
                                event_data[dt_field] = dt_value
                            elif isinstance(dt_value, date):
                                # dateをdatetimeに変換
                                event_data[dt_field] = datetime.combine(dt_value, datetime.min.time())
                    
                    events.append(event_data)
            
            # 日付順にソート
            events.sort(key=lambda x: x['dtstart'] if x['dtstart'] else datetime.min)
            
            self.logger.info(f"イベント抽出完了: {len(events)} 件")
            
            return events
            
        except Exception as e:
            raise ICSAnalysisError(f"イベント抽出失敗: {e}")
    
    def analyze_events(self, events: List[Dict]) -> Dict:
        """イベント分析・統計生成.
        
        要件3: 統計情報表示
        
        Args:
            events: イベントリスト
            
        Returns:
            統計情報辞書
        """
        try:
            total_events = len(events)
            
            if total_events == 0:
                return {
                    'total_events': 0,
                    'date_range': None,
                    'holiday_types': {},
                    'yearly_distribution': {},
                    'monthly_distribution': {}
                }
            
            # カテゴリ別集計
            holiday_types = Counter()
            yearly_distribution = Counter()
            monthly_distribution = Counter()
            
            # 日付範囲計算
            valid_dates = []
            
            for event in events:
                # カテゴリ分類
                categories = event.get('categories', '')
                summary = event.get('summary', '')
                
                if 'Japanese-Holiday' in categories:
                    holiday_types['国民の祝日'] += 1
                elif '振替休日' in summary:
                    holiday_types['振替休日'] += 1
                elif '国民の休日' in summary:
                    holiday_types['国民の休日'] += 1
                else:
                    holiday_types['その他'] += 1
                
                # 日付分析
                if event['dtstart']:
                    dt = event['dtstart']
                    valid_dates.append(dt)
                    yearly_distribution[dt.year] += 1
                    monthly_distribution[dt.month] += 1
            
            # 日付範囲
            date_range = None
            if valid_dates:
                valid_dates.sort()
                date_range = {
                    'start': valid_dates[0].date(),
                    'end': valid_dates[-1].date(),
                    'span_days': (valid_dates[-1].date() - valid_dates[0].date()).days
                }
            
            return {
                'total_events': total_events,
                'date_range': date_range,
                'holiday_types': dict(holiday_types),
                'yearly_distribution': dict(yearly_distribution),
                'monthly_distribution': dict(monthly_distribution)
            }
            
        except Exception as e:
            raise ICSAnalysisError(f"イベント分析失敗: {e}")
    
    def validate_ics_format(self, calendar: Calendar) -> List[str]:
        """ICS形式検証・エラー検出.
        
        要件3: エラー検出
        
        Args:
            calendar: icalendarオブジェクト
            
        Returns:
            検出されたエラーリスト
        """
        try:
            errors = []
            
            # 基本プロパティ確認
            if 'prodid' not in calendar:
                errors.append("必須プロパティPRODIDが不足")
            
            if 'version' not in calendar:
                errors.append("必須プロパティVERSIONが不足")
            
            # イベント検証
            event_uids = set()
            
            for component in calendar.walk():
                if component.name == "VEVENT":
                    # 必須プロパティ確認
                    required_props = ['uid', 'dtstart', 'dtstamp']
                    for prop in required_props:
                        if prop not in component:
                            errors.append(f"イベントの必須プロパティ{prop.upper()}が不足")
                    
                    # UID重複確認
                    if 'uid' in component:
                        uid = str(component['uid'])
                        if uid in event_uids:
                            errors.append(f"重複するUID: {uid}")
                        else:
                            event_uids.add(uid)
                    
                    # 日付形式確認
                    for dt_prop in ['dtstart', 'dtend']:
                        if dt_prop in component:
                            try:
                                dt_value = component[dt_prop].dt
                                if not isinstance(dt_value, (datetime, date)):
                                    errors.append(f"不正な日付形式: {dt_prop}")
                            except Exception:
                                errors.append(f"日付解析エラー: {dt_prop}")
            
            self.logger.info(f"ICS形式検証完了: {len(errors)} 件のエラー")
            
            return errors
            
        except Exception as e:
            return [f"検証処理エラー: {e}"]
    
    def format_human_readable(self, analysis: Dict = None) -> str:
        """人間可読形式フォーマット.
        
        要件3: 人間可読形式出力
        
        Args:
            analysis: 解析結果（省略時は最後の解析結果を使用）
            
        Returns:
            人間可読形式の文字列
        """
        if analysis is None:
            analysis = self.analysis_result
        
        if not analysis:
            return "解析結果がありません"
        
        try:
            output = []
            
            # ヘッダー
            output.append("=" * 60)
            output.append("ICSファイル解析結果")
            output.append("=" * 60)
            
            # ファイル情報
            file_info = analysis['file_info']
            output.append(f"ファイル: {file_info['filepath']}")
            output.append(f"サイズ: {file_info['file_size']:,} bytes")
            output.append(f"解析日時: {file_info['analysis_date']}")
            
            # 統計情報
            stats = analysis['statistics']
            output.append(f"\n=== 統計情報 ===")
            output.append(f"総イベント数: {stats['total_events']} 件")
            
            if stats['date_range']:
                date_range = stats['date_range']
                output.append(f"対象期間: {date_range['start']} - {date_range['end']}")
                output.append(f"期間: {date_range['span_days']} 日間")
            
            # 祝日種類別集計
            if stats['holiday_types']:
                output.append(f"\n=== 祝日種類別集計 ===")
                for holiday_type, count in stats['holiday_types'].items():
                    output.append(f"- {holiday_type}: {count} 件")
            
            # 年別分布
            if stats['yearly_distribution']:
                output.append(f"\n=== 年別分布 ===")
                for year, count in sorted(stats['yearly_distribution'].items()):
                    output.append(f"- {year}年: {count} 件")
            
            # イベント一覧（最初の10件）
            events = analysis['events']
            if events:
                output.append(f"\n=== イベント一覧（最初の10件） ===")
                output.append(f"{'日付':<12} {'祝日名':<20} {'カテゴリ':<15} {'UID'}")
                output.append("-" * 80)
                
                for event in events[:10]:
                    date_str = event['dtstart'].strftime('%Y-%m-%d') if event['dtstart'] else 'N/A'
                    summary = event['summary'][:18] + '..' if len(event['summary']) > 20 else event['summary']
                    categories = event['categories'][:13] + '..' if len(event['categories']) > 15 else event['categories']
                    uid = event['uid'][:30] + '..' if len(event['uid']) > 32 else event['uid']
                    
                    output.append(f"{date_str:<12} {summary:<20} {categories:<15} {uid}")
                
                if len(events) > 10:
                    output.append(f"... 他 {len(events) - 10} 件")
            
            # 検証エラー
            errors = analysis['validation_errors']
            if errors:
                output.append(f"\n=== 検証エラー ===")
                for error in errors:
                    output.append(f"⚠️  {error}")
            else:
                output.append(f"\n✅ 検証エラーなし")
            
            return '\n'.join(output)
            
        except Exception as e:
            return f"フォーマットエラー: {e}"
    
    def export_json(self, analysis: Dict = None) -> str:
        """JSON形式エクスポート.
        
        要件3: 複数形式対応
        
        Args:
            analysis: 解析結果（省略時は最後の解析結果を使用）
            
        Returns:
            JSON形式の文字列
        """
        if analysis is None:
            analysis = self.analysis_result
        
        if not analysis:
            return "{}"
        
        try:
            # datetimeオブジェクトをJSON serializable形式に変換
            def json_serializer(obj):
                if isinstance(obj, (datetime, date)):
                    return obj.isoformat()
                raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
            
            return json.dumps(analysis, ensure_ascii=False, indent=2, default=json_serializer)
            
        except Exception as e:
            return f'{{"error": "JSON export failed: {e}"}}'
    
    def export_csv(self, events: List[Dict] = None) -> str:
        """CSV形式エクスポート.
        
        要件3: 複数形式対応
        
        Args:
            events: イベントリスト（省略時は最後の解析結果を使用）
            
        Returns:
            CSV形式の文字列
        """
        if events is None and self.analysis_result:
            events = self.analysis_result['events']
        
        if not events:
            return ""
        
        try:
            output = io.StringIO()
            writer = csv.writer(output)
            
            # ヘッダー
            writer.writerow(['日付', '祝日名', '説明', 'カテゴリ', 'UID'])
            
            # データ
            for event in events:
                date_str = event['dtstart'].strftime('%Y-%m-%d') if event['dtstart'] else ''
                writer.writerow([
                    date_str,
                    event['summary'],
                    event['description'],
                    event['categories'],
                    event['uid']
                ])
            
            return output.getvalue()
            
        except Exception as e:
            return f"CSV export failed: {e}"
    
    def format_simple_output(self, analysis: Dict = None) -> str:
        """簡易出力フォーマット.
        
        要件3拡張: 簡易的な出力（サマリー + リスト）
        
        Args:
            analysis: 解析結果（省略時は最後の解析結果を使用）
            
        Returns:
            簡易形式の文字列
        """
        if analysis is None:
            analysis = self.analysis_result
        
        if not analysis:
            return "解析結果がありません"
        
        try:
            output = []
            
            # サマリー部分
            file_info = analysis['file_info']
            stats = analysis['statistics']
            
            output.append("=== サマリー ===")
            output.append(f"ファイル: {Path(file_info['filepath']).name}")
            output.append(f"総イベント数: {stats['total_events']} 件")
            
            if stats['date_range']:
                date_range = stats['date_range']
                output.append(f"期間: {date_range['start']} - {date_range['end']}")
            
            # 年別分布（簡潔に）
            if stats['yearly_distribution']:
                year_summary = []
                for year, count in sorted(stats['yearly_distribution'].items()):
                    year_summary.append(f"{year}年({count}件)")
                output.append(f"年別: {', '.join(year_summary)}")
            
            # 検証エラー
            errors = analysis['validation_errors']
            if errors:
                output.append(f"エラー: {len(errors)} 件")
            else:
                output.append("エラー: なし")
            
            # リスト部分
            events = analysis['events']
            if events:
                output.append(f"\n=== イベント一覧 ===")
                
                for event in events:
                    # イベント名
                    event_name = event['summary']
                    
                    # イベント期間（ISO8601形式）
                    period = self._format_event_period(event)
                    
                    output.append(f"{event_name} | {period}")
            
            return '\n'.join(output)
            
        except Exception as e:
            return f"簡易出力フォーマットエラー: {e}"
    
    def _format_event_period(self, event: Dict) -> str:
        """イベント期間のフォーマット.
        
        Args:
            event: イベント辞書
            
        Returns:
            ISO8601形式の期間文字列
        """
        try:
            start_dt = event['dtstart']
            end_dt = event['dtend']
            
            if not start_dt:
                return "期間不明"
            
            # 終日イベントかどうかの判定
            # 開始時刻が00:00:00で、終了時刻が翌日の00:00:00の場合は終日イベント
            is_all_day = False
            
            if start_dt and end_dt:
                # 開始時刻が00:00:00かつ終了時刻が翌日の00:00:00
                if (start_dt.time() == datetime.min.time() and 
                    end_dt.time() == datetime.min.time() and
                    (end_dt.date() - start_dt.date()).days == 1):
                    is_all_day = True
            
            if is_all_day:
                # 終日イベント: 日付のみ（ISO8601形式）
                return start_dt.date().isoformat()
            else:
                # 時刻指定イベント: 開始-終了（ISO8601形式）
                if end_dt:
                    return f"{start_dt.isoformat()} - {end_dt.isoformat()}"
                else:
                    return start_dt.isoformat()
                    
        except Exception as e:
            return f"期間フォーマットエラー: {e}"
    
    def compare_ics_files(self, file1_path: str, file2_path: str) -> Dict:
        """2つのICSファイル比較.
        
        要件4: ファイル比較機能
        
        Args:
            file1_path: 比較元ICSファイルパス
            file2_path: 比較先ICSファイルパス
            
        Returns:
            比較結果辞書
            
        Raises:
            ICSAnalysisError: 比較エラー
        """
        try:
            self.logger.info(f"ICSファイル比較開始: {file1_path} vs {file2_path}")
            
            # 両ファイルを解析
            analysis1 = self.parse_ics_file(file1_path)
            analysis2 = self.parse_ics_file(file2_path)
            
            events1 = analysis1['events']
            events2 = analysis2['events']
            
            # 変更検出
            changes = self.detect_event_changes(events1, events2)
            
            # 比較結果構築
            comparison_result = {
                'file1_info': {
                    'filepath': file1_path,
                    'total_events': len(events1)
                },
                'file2_info': {
                    'filepath': file2_path,
                    'total_events': len(events2)
                },
                'summary': {
                    'added': len(changes['added']),
                    'deleted': len(changes['deleted']),
                    'modified': len(changes['modified']),
                    'unchanged': len(changes['unchanged'])
                },
                'changes': changes,
                'comparison_date': datetime.now().isoformat()
            }
            
            self.logger.info(f"ICSファイル比較完了: 追加{len(changes['added'])}件、削除{len(changes['deleted'])}件、変更{len(changes['modified'])}件")
            
            return comparison_result
            
        except Exception as e:
            if isinstance(e, ICSAnalysisError):
                raise
            else:
                raise ICSAnalysisError(f"ICSファイル比較失敗: {e}")
    
    def detect_event_changes(self, events1: List[Dict], events2: List[Dict]) -> Dict:
        """イベントレベルでの変更検出.
        
        要件4: 変更種別表示
        
        Args:
            events1: 比較元イベントリスト
            events2: 比較先イベントリスト
            
        Returns:
            変更検出結果
        """
        try:
            # UIDをキーとした辞書作成
            events1_dict = {event['uid']: event for event in events1 if event['uid']}
            events2_dict = {event['uid']: event for event in events2 if event['uid']}
            
            # UIDがないイベントはDTSTARTで照合
            events1_no_uid = [event for event in events1 if not event['uid']]
            events2_no_uid = [event for event in events2 if not event['uid']]
            
            # UIDベースの比較
            uid1_set = set(events1_dict.keys())
            uid2_set = set(events2_dict.keys())
            
            added_uids = uid2_set - uid1_set
            deleted_uids = uid1_set - uid2_set
            common_uids = uid1_set & uid2_set
            
            # 変更検出結果
            changes = {
                'added': [],
                'deleted': [],
                'modified': [],
                'unchanged': []
            }
            
            # 追加されたイベント
            for uid in added_uids:
                event = events2_dict[uid]
                changes['added'].append({
                    'event': event,
                    'change_type': 'added'
                })
            
            # 削除されたイベント
            for uid in deleted_uids:
                event = events1_dict[uid]
                changes['deleted'].append({
                    'event': event,
                    'change_type': 'deleted'
                })
            
            # 共通UIDの変更確認
            for uid in common_uids:
                event1 = events1_dict[uid]
                event2 = events2_dict[uid]
                
                property_changes = self.compare_event_properties(event1, event2)
                
                if property_changes:
                    changes['modified'].append({
                        'event1': event1,
                        'event2': event2,
                        'property_changes': property_changes,
                        'change_type': 'modified'
                    })
                else:
                    changes['unchanged'].append({
                        'event': event1,
                        'change_type': 'unchanged'
                    })
            
            # UIDなしイベントの処理（DTSTARTベース）
            # 簡易実装: 同じDTSTARTのイベントを照合
            dtstart1_dict = {event['dtstart'].isoformat() if event['dtstart'] else '': event 
                           for event in events1_no_uid}
            dtstart2_dict = {event['dtstart'].isoformat() if event['dtstart'] else '': event 
                           for event in events2_no_uid}
            
            dtstart1_set = set(dtstart1_dict.keys())
            dtstart2_set = set(dtstart2_dict.keys())
            
            # DTSTARTベースの追加・削除
            for dtstart in dtstart2_set - dtstart1_set:
                if dtstart:  # 空文字列は除外
                    event = dtstart2_dict[dtstart]
                    changes['added'].append({
                        'event': event,
                        'change_type': 'added'
                    })
            
            for dtstart in dtstart1_set - dtstart2_set:
                if dtstart:  # 空文字列は除外
                    event = dtstart1_dict[dtstart]
                    changes['deleted'].append({
                        'event': event,
                        'change_type': 'deleted'
                    })
            
            # 時系列ソート
            for change_type in ['added', 'deleted', 'modified']:
                changes[change_type].sort(key=lambda x: self._get_event_sort_key(x))
            
            return changes
            
        except Exception as e:
            raise ICSAnalysisError(f"変更検出失敗: {e}")
    
    def compare_event_properties(self, event1: Dict, event2: Dict) -> List[str]:
        """イベントプロパティの詳細比較.
        
        要件4: 詳細差分表示
        
        Args:
            event1: 比較元イベント
            event2: 比較先イベント
            
        Returns:
            変更されたプロパティのリスト
        """
        try:
            changes = []
            
            # 比較対象プロパティ
            compare_props = ['summary', 'description', 'categories', 'dtstart', 'dtend']
            
            for prop in compare_props:
                value1 = event1.get(prop)
                value2 = event2.get(prop)
                
                # datetime型の比較
                if isinstance(value1, datetime) and isinstance(value2, datetime):
                    if value1 != value2:
                        changes.append(f"{prop.upper()}: {value1.isoformat()} → {value2.isoformat()}")
                # 文字列の比較
                elif str(value1) != str(value2):
                    changes.append(f"{prop.upper()}: {value1} → {value2}")
            
            return changes
            
        except Exception as e:
            self.logger.warning(f"プロパティ比較エラー: {e}")
            return []
    
    def _get_event_sort_key(self, change_item: Dict):
        """変更アイテムのソートキー取得.
        
        Args:
            change_item: 変更アイテム
            
        Returns:
            ソート用キー
        """
        try:
            # イベント取得
            if 'event' in change_item:
                event = change_item['event']
            elif 'event2' in change_item:  # modified の場合
                event = change_item['event2']
            else:
                return datetime.min
            
            # DTSTARTでソート
            if event.get('dtstart'):
                return event['dtstart']
            else:
                return datetime.min
                
        except Exception:
            return datetime.min
    
    def format_comparison_result(self, comparison: Dict) -> str:
        """比較結果の人間可読形式フォーマット.
        
        要件4: 時系列ソート、変更種別表示
        
        Args:
            comparison: 比較結果辞書
            
        Returns:
            人間可読形式の文字列
        """
        try:
            output = []
            
            # ヘッダー
            output.append("=" * 70)
            output.append("ICSファイル比較結果")
            output.append("=" * 70)
            
            # ファイル情報
            file1_info = comparison['file1_info']
            file2_info = comparison['file2_info']
            
            output.append(f"ファイル1: {Path(file1_info['filepath']).name} ({file1_info['total_events']}イベント)")
            output.append(f"ファイル2: {Path(file2_info['filepath']).name} ({file2_info['total_events']}イベント)")
            
            # 変更サマリー
            summary = comparison['summary']
            output.append(f"\n=== 変更サマリー ===")
            output.append(f"追加: {summary['added']}件")
            output.append(f"削除: {summary['deleted']}件")
            output.append(f"変更: {summary['modified']}件")
            output.append(f"未変更: {summary['unchanged']}件")
            
            # 詳細差分
            changes = comparison['changes']
            
            # 削除されたイベント
            if changes['deleted']:
                output.append(f"\n=== 削除されたイベント ===")
                for item in changes['deleted']:
                    event = item['event']
                    date_str = event['dtstart'].strftime('%Y-%m-%d') if event['dtstart'] else 'N/A'
                    output.append(f"[削除] {date_str} {event['summary']} ({event['uid']})")
            
            # 追加されたイベント
            if changes['added']:
                output.append(f"\n=== 追加されたイベント ===")
                for item in changes['added']:
                    event = item['event']
                    date_str = event['dtstart'].strftime('%Y-%m-%d') if event['dtstart'] else 'N/A'
                    output.append(f"[追加] {date_str} {event['summary']} ({event['uid']})")
            
            # 変更されたイベント
            if changes['modified']:
                output.append(f"\n=== 変更されたイベント ===")
                for item in changes['modified']:
                    event2 = item['event2']
                    date_str = event2['dtstart'].strftime('%Y-%m-%d') if event2['dtstart'] else 'N/A'
                    output.append(f"[変更] {date_str} {event2['summary']} ({event2['uid']})")
                    
                    # プロパティ変更詳細
                    for prop_change in item['property_changes']:
                        output.append(f"  - {prop_change}")
            
            return '\n'.join(output)
            
        except Exception as e:
            return f"比較結果フォーマットエラー: {e}"
    
    def export_comparison_json(self, comparison: Dict) -> str:
        """比較結果のJSON形式エクスポート.
        
        要件4: 複数形式対応
        
        Args:
            comparison: 比較結果辞書
            
        Returns:
            JSON形式の文字列
        """
        try:
            # datetimeオブジェクトをJSON serializable形式に変換
            def json_serializer(obj):
                if isinstance(obj, (datetime, date)):
                    return obj.isoformat()
                raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
            
            return json.dumps(comparison, ensure_ascii=False, indent=2, default=json_serializer)
            
        except Exception as e:
            return f'{{"error": "Comparison JSON export failed: {e}"}}'
    
    def _analyze_time_patterns(self) -> Dict:
        """Analyze time patterns in the calendar.
        
        Returns:
            Time pattern analysis
        """
        monthly_distribution = defaultdict(int)
        yearly_distribution = defaultdict(int)
        weekday_distribution = defaultdict(int)
        duration_analysis = []
        
        for event in self.events:
            if 'DTSTART' in event:
                start_date = self._extract_date_from_ics(event['DTSTART'])
                if start_date:
                    dt = datetime.fromisoformat(start_date)
                    monthly_distribution[dt.month] += 1
                    yearly_distribution[dt.year] += 1
                    weekday_distribution[dt.strftime('%A')] += 1
                    
                    # Calculate duration if end date exists
                    if 'DTEND' in event:
                        end_date = self._extract_date_from_ics(event['DTEND'])
                        if end_date:
                            end_dt = datetime.fromisoformat(end_date)
                            duration = (end_dt - dt).days
                            duration_analysis.append(duration)
        
        # Convert month numbers to names
        month_names = {i: cal.month_name[i] for i in range(1, 13)}
        monthly_named = {month_names[month]: count for month, count in monthly_distribution.items()}
        
        # Calculate duration statistics
        duration_stats = {}
        if duration_analysis:
            duration_stats = {
                'average_duration': sum(duration_analysis) / len(duration_analysis),
                'min_duration': min(duration_analysis),
                'max_duration': max(duration_analysis),
                'total_blocked_days': sum(duration_analysis)
            }
        
        return {
            'monthly_distribution': monthly_named,
            'yearly_distribution': dict(yearly_distribution),
            'weekday_distribution': dict(weekday_distribution),
            'duration_statistics': duration_stats
        }
    
    def _analyze_events(self) -> Dict:
        """Analyze event characteristics.
        
        Returns:
            Event analysis results
        """
        event_types = Counter()
        japanese_holidays = 0
        custom_events = 0
        
        for event in self.events:
            summary = event.get('SUMMARY', '')
            categories = event.get('CATEGORIES', '')
            
            # Classify event types
            if '日本の祝日' in summary or 'Japanese-Holiday' in categories:
                japanese_holidays += 1
                event_types['Japanese Holiday'] += 1
            elif 'maintenance' in summary.lower():
                event_types['Maintenance'] += 1
                custom_events += 1
            elif 'deployment' in summary.lower():
                event_types['Deployment'] += 1
                custom_events += 1
            else:
                event_types['Other'] += 1
                custom_events += 1
        
        # Find upcoming events
        upcoming_events = self._find_upcoming_events()
        
        return {
            'event_types': dict(event_types),
            'japanese_holidays_count': japanese_holidays,
            'custom_events_count': custom_events,
            'upcoming_events': upcoming_events
        }
    
    def _analyze_coverage(self) -> Dict:
        """Analyze calendar coverage and gaps.
        
        Returns:
            Coverage analysis results
        """
        if not self.events:
            return {'coverage_percentage': 0, 'gaps': [], 'busy_periods': []}
        
        # Get all event dates
        event_dates = set()
        for event in self.events:
            if 'DTSTART' in event and 'DTEND' in event:
                start_date = self._extract_date_from_ics(event['DTSTART'])
                end_date = self._extract_date_from_ics(event['DTEND'])
                
                if start_date and end_date:
                    start_dt = datetime.fromisoformat(start_date).date()
                    end_dt = datetime.fromisoformat(end_date).date()
                    
                    # Add all dates in the range
                    current_date = start_dt
                    while current_date < end_dt:
                        event_dates.add(current_date)
                        current_date += timedelta(days=1)
        
        if not event_dates:
            return {'coverage_percentage': 0, 'gaps': [], 'busy_periods': []}
        
        # Calculate coverage for current year
        current_year = datetime.now().year
        year_start = date(current_year, 1, 1)
        year_end = date(current_year, 12, 31)
        
        total_days = (year_end - year_start).days + 1
        covered_days = len([d for d in event_dates if d.year == current_year])
        coverage_percentage = (covered_days / total_days) * 100
        
        # Find gaps (periods with no events)
        gaps = self._find_gaps(event_dates, current_year)
        
        # Find busy periods (consecutive event days)
        busy_periods = self._find_busy_periods(event_dates, current_year)
        
        return {
            'coverage_percentage': round(coverage_percentage, 2),
            'covered_days': covered_days,
            'total_days': total_days,
            'gaps': gaps,
            'busy_periods': busy_periods
        }
    
    def _find_upcoming_events(self, days_ahead: int = 30) -> List[Dict]:
        """Find upcoming events within specified days.
        
        Args:
            days_ahead: Number of days to look ahead
            
        Returns:
            List of upcoming events
        """
        today = datetime.now().date()
        cutoff_date = today + timedelta(days=days_ahead)
        
        upcoming = []
        for event in self.events:
            if 'DTSTART' in event:
                start_date = self._extract_date_from_ics(event['DTSTART'])
                if start_date:
                    event_date = datetime.fromisoformat(start_date).date()
                    if today <= event_date <= cutoff_date:
                        days_until = (event_date - today).days
                        upcoming.append({
                            'summary': event.get('SUMMARY', 'Unknown Event'),
                            'date': start_date,
                            'days_until': days_until,
                            'categories': event.get('CATEGORIES', '')
                        })
        
        # Sort by date
        upcoming.sort(key=lambda x: x['date'])
        return upcoming[:10]  # Return top 10
    
    def _find_gaps(self, event_dates: set, year: int) -> List[Dict]:
        """Find gaps in calendar coverage.
        
        Args:
            event_dates: Set of dates with events
            year: Year to analyze
            
        Returns:
            List of gap periods
        """
        gaps = []
        year_dates = [d for d in event_dates if d.year == year]
        
        if not year_dates:
            return gaps
        
        year_dates = sorted(year_dates)
        
        # Find gaps between events
        for i in range(len(year_dates) - 1):
            current_date = year_dates[i]
            next_date = year_dates[i + 1]
            gap_days = (next_date - current_date).days - 1
            
            if gap_days > 7:  # Only report gaps longer than a week
                gaps.append({
                    'start_date': (current_date + timedelta(days=1)).isoformat(),
                    'end_date': (next_date - timedelta(days=1)).isoformat(),
                    'gap_days': gap_days
                })
        
        return gaps[:5]  # Return top 5 gaps
    
    def _find_busy_periods(self, event_dates: set, year: int) -> List[Dict]:
        """Find busy periods with consecutive events.
        
        Args:
            event_dates: Set of dates with events
            year: Year to analyze
            
        Returns:
            List of busy periods
        """
        busy_periods = []
        year_dates = sorted([d for d in event_dates if d.year == year])
        
        if not year_dates:
            return busy_periods
        
        current_period_start = year_dates[0]
        current_period_end = year_dates[0]
        
        for i in range(1, len(year_dates)):
            if (year_dates[i] - current_period_end).days <= 1:
                # Consecutive or same day
                current_period_end = year_dates[i]
            else:
                # Gap found, save current period if it's significant
                period_days = (current_period_end - current_period_start).days + 1
                if period_days > 3:  # Only report periods longer than 3 days
                    busy_periods.append({
                        'start_date': current_period_start.isoformat(),
                        'end_date': current_period_end.isoformat(),
                        'duration_days': period_days
                    })
                
                current_period_start = year_dates[i]
                current_period_end = year_dates[i]
        
        # Don't forget the last period
        period_days = (current_period_end - current_period_start).days + 1
        if period_days > 3:
            busy_periods.append({
                'start_date': current_period_start.isoformat(),
                'end_date': current_period_end.isoformat(),
                'duration_days': period_days
            })
        
        return busy_periods[:5]  # Return top 5 busy periods
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on analysis.
        
        Returns:
            List of recommendations
        """
        recommendations = []
        
        if not self.events:
            recommendations.append("カレンダーにイベントがありません。祝日や定期メンテナンスの追加を検討してください。")
            return recommendations
        
        # Check for Japanese holidays
        japanese_holidays = sum(1 for event in self.events 
                              if '日本の祝日' in event.get('SUMMARY', '') or 
                                 'Japanese-Holiday' in event.get('CATEGORIES', ''))
        
        if japanese_holidays == 0:
            recommendations.append("日本の祝日が設定されていません。祝日期間中の作業を避けるため、祝日の追加を推奨します。")
        elif japanese_holidays < 15:
            recommendations.append("祝日の設定が不完全な可能性があります。年間の全祝日が含まれているか確認してください。")
        
        # Check coverage
        basic_stats = self._get_basic_statistics()
        if basic_stats.get('date_range', {}).get('span_days', 0) < 365:
            recommendations.append("カレンダーの対象期間が1年未満です。年間を通じたカバレッジの確保を検討してください。")
        
        # Check for maintenance patterns
        maintenance_events = sum(1 for event in self.events 
                               if 'maintenance' in event.get('SUMMARY', '').lower())
        
        if maintenance_events == 0:
            recommendations.append("定期メンテナンスのスケジュールが設定されていません。計画的なメンテナンス期間の追加を検討してください。")
        
        # Check for weekend coverage
        time_analysis = self._analyze_time_patterns()
        weekday_dist = time_analysis.get('weekday_distribution', {})
        weekend_events = weekday_dist.get('Saturday', 0) + weekday_dist.get('Sunday', 0)
        total_events = sum(weekday_dist.values())
        
        if total_events > 0 and (weekend_events / total_events) < 0.1:
            recommendations.append("週末のイベントが少ないです。週末メンテナンスの機会を活用することを検討してください。")
        
        return recommendations
    
    def _extract_date_from_ics(self, ics_datetime: str) -> Optional[str]:
        """Extract date from ICS datetime string.
        
        Args:
            ics_datetime: ICS datetime string
            
        Returns:
            ISO format date string or None
        """
        try:
            # Handle different ICS datetime formats
            if 'T' in ics_datetime:
                # YYYYMMDDTHHMMSS format
                date_part = ics_datetime.split('T')[0]
                if len(date_part) == 8:
                    year = date_part[:4]
                    month = date_part[4:6]
                    day = date_part[6:8]
                    return f"{year}-{month}-{day}"
            elif len(ics_datetime) == 8:
                # YYYYMMDD format
                year = ics_datetime[:4]
                month = ics_datetime[4:6]
                day = ics_datetime[6:8]
                return f"{year}-{month}-{day}"
        except (ValueError, IndexError):
            pass
        
        return None
    
    def generate_event_semantic_diff(self, file1: str, file2: str) -> Dict:
        """イベント意味的Diff生成.
        
        要件4.2: イベント単位での意味的diff形式表示
        
        Args:
            file1: 比較元ICSファイルパス
            file2: 比較先ICSファイルパス
            
        Returns:
            意味的diff結果辞書
            
        Raises:
            ICSAnalysisError: 意味的diff生成エラー
        """
        try:
            self.logger.info(f"イベント意味的Diff生成開始: {file1} vs {file2}")
            
            # 両ファイルを解析
            analysis1 = self.parse_ics_file(file1)
            analysis2 = self.parse_ics_file(file2)
            
            events1 = analysis1['events']
            events2 = analysis2['events']
            
            # 詳細なイベント変更検出
            changes = self.detect_event_changes_detailed(events1, events2)
            
            # 統計情報計算
            statistics = {
                'added': len(changes['added']),
                'deleted': len(changes['deleted']),
                'modified': len(changes['modified']),
                'moved': len(changes['moved']),
                'duration_changed': len(changes['duration_changed']),
                'unchanged': len(events1) + len(events2) - len(changes['added']) - len(changes['deleted']) - len(changes['modified']) - len(changes['moved']) - len(changes['duration_changed'])
            }
            
            # 日付順ソート
            sorted_changes = self._sort_changes_chronologically(changes)
            
            # 意味的diff結果構築
            semantic_diff_result = {
                'file1_info': {
                    'filepath': file1,
                    'events': len(events1)
                },
                'file2_info': {
                    'filepath': file2,
                    'events': len(events2)
                },
                'statistics': statistics,
                'changes': changes,
                'sorted_changes': sorted_changes,
                'diff_date': datetime.now().isoformat()
            }
            
            self.logger.info(f"意味的Diff生成完了: 追加{statistics['added']}件, 削除{statistics['deleted']}件, 変更{statistics['modified']}件, 移動{statistics['moved']}件, 期間変更{statistics['duration_changed']}件")
            
            return semantic_diff_result
            
        except Exception as e:
            if isinstance(e, ICSAnalysisError):
                raise
            else:
                raise ICSAnalysisError(f"イベント意味的Diff生成失敗: {e}")
    
    def detect_event_changes_detailed(self, events1: List[Dict], events2: List[Dict]) -> Dict:
        """詳細なイベント変更検出.
        
        要件4.2: UID主キー + DTSTART/SUMMARY副キー照合
        
        Args:
            events1: ファイル1のイベントリスト
            events2: ファイル2のイベントリスト
            
        Returns:
            詳細変更辞書
        """
        try:
            # UID主キー照合用辞書作成
            events1_by_uid = {event['uid']: event for event in events1 if event['uid']}
            events2_by_uid = {event['uid']: event for event in events2 if event['uid']}
            
            changes = {
                'added': [],           # ファイル2にのみ存在
                'deleted': [],         # ファイル1にのみ存在
                'modified': [],        # プロパティ変更
                'moved': [],           # 日時変更
                'duration_changed': [] # 期間変更
            }
            
            # ファイル2のイベントをチェック（追加・変更検出）
            for uid, event2 in events2_by_uid.items():
                if uid not in events1_by_uid:
                    # 追加されたイベント
                    changes['added'].append({
                        'event': event2,
                        'change_type': 'added',
                        'uid': uid
                    })
                else:
                    # 既存イベントの変更チェック
                    event1 = events1_by_uid[uid]
                    change_type = self.classify_event_changes(event1, event2)
                    
                    if change_type != 'unchanged':
                        change_details = self._get_detailed_property_changes(event1, event2)
                        
                        changes[change_type].append({
                            'event1': event1,
                            'event2': event2,
                            'changes': change_details,
                            'change_type': change_type,
                            'uid': uid
                        })
            
            # ファイル1のイベントをチェック（削除検出）
            for uid, event1 in events1_by_uid.items():
                if uid not in events2_by_uid:
                    # 削除されたイベント
                    changes['deleted'].append({
                        'event': event1,
                        'change_type': 'deleted',
                        'uid': uid
                    })
            
            return changes
            
        except Exception as e:
            raise ICSAnalysisError(f"詳細イベント変更検出失敗: {e}")
    
    def classify_event_changes(self, event1: Dict, event2: Dict) -> str:
        """イベント変更種別分類.
        
        要件4.2: 変更種別検出
        
        Args:
            event1: 比較元イベント
            event2: 比較先イベント
            
        Returns:
            変更種別 ('unchanged', 'modified', 'moved', 'duration_changed')
        """
        try:
            # 日時変更チェック
            dtstart_changed = event1.get('dtstart') != event2.get('dtstart')
            dtend_changed = event1.get('dtend') != event2.get('dtend')
            
            if dtstart_changed or dtend_changed:
                # 期間長変更チェック
                if event1.get('dtstart') and event1.get('dtend') and event2.get('dtstart') and event2.get('dtend'):
                    duration1 = event1['dtend'] - event1['dtstart']
                    duration2 = event2['dtend'] - event2['dtstart']
                    
                    if duration1 != duration2:
                        return 'duration_changed'
                    else:
                        return 'moved'
                else:
                    return 'moved'
            
            # プロパティ変更チェック
            properties_to_check = ['summary', 'description', 'categories']
            for prop in properties_to_check:
                if str(event1.get(prop, '')) != str(event2.get(prop, '')):
                    return 'modified'
            
            return 'unchanged'
            
        except Exception as e:
            self.logger.warning(f"イベント変更分類エラー: {e}")
            return 'modified'  # エラー時はmodifiedとして扱う
    
    def _get_detailed_property_changes(self, event1: Dict, event2: Dict) -> List[Dict]:
        """詳細なプロパティ変更取得.
        
        Args:
            event1: 比較元イベント
            event2: 比較先イベント
            
        Returns:
            変更されたプロパティのリスト
        """
        changes = []
        
        # 比較対象プロパティ
        compare_props = ['summary', 'description', 'categories', 'dtstart', 'dtend']
        
        for prop in compare_props:
            value1 = event1.get(prop)
            value2 = event2.get(prop)
            
            # datetime/dateオブジェクトの比較
            if isinstance(value1, (datetime, date)) and isinstance(value2, (datetime, date)):
                if value1 != value2:
                    changes.append({
                        'property': prop,
                        'old_value': value1.isoformat() if value1 else None,
                        'new_value': value2.isoformat() if value2 else None,
                        'change_type': 'datetime'
                    })
            else:
                # 文字列比較
                str_value1 = str(value1) if value1 else ''
                str_value2 = str(value2) if value2 else ''
                
                if str_value1 != str_value2:
                    changes.append({
                        'property': prop,
                        'old_value': str_value1,
                        'new_value': str_value2,
                        'change_type': 'string'
                    })
        
        return changes
    
    def _sort_changes_chronologically(self, changes: Dict) -> List[Dict]:
        """変更を時系列順にソート.
        
        要件4.2: 日付順ソート
        
        Args:
            changes: 変更辞書
            
        Returns:
            日付順ソート済み変更リスト
        """
        all_changes = []
        
        # 各変更種別から変更を収集
        for change_type, change_list in changes.items():
            for change in change_list:
                # ソート用の日時を取得
                if change_type == 'added':
                    sort_date = change['event'].get('dtstart', datetime.min)
                elif change_type == 'deleted':
                    sort_date = change['event'].get('dtstart', datetime.min)
                else:
                    # modified, moved, duration_changed
                    sort_date = change['event2'].get('dtstart', datetime.min)
                
                all_changes.append({
                    'change_type': change_type,
                    'sort_date': sort_date,
                    'change_data': change
                })
        
        # 日付順ソート
        all_changes.sort(key=lambda x: x['sort_date'] if x['sort_date'] else datetime.min)
        
        return all_changes
    
    def format_semantic_diff(self, diff_data: Dict, use_color: bool = False) -> str:
        """意味的Diff出力フォーマット.
        
        要件4.2: 構造化diff形式（人間可読）
        
        Args:
            diff_data: 意味的diff結果辞書
            use_color: カラー出力使用フラグ
            
        Returns:
            フォーマットされた意味的diff文字列
        """
        try:
            output = []
            
            # カラーコード定義
            colors = {
                'added': '\033[32m',      # Green (+)
                'deleted': '\033[31m',    # Red (-)
                'modified': '\033[33m',   # Yellow (~)
                'moved': '\033[34m',      # Blue (=)
                'duration_changed': '\033[35m',  # Magenta (Δ)
                'header': '\033[1m',      # Bold
                'reset': '\033[0m'        # Reset
            } if use_color else {key: '' for key in ['added', 'deleted', 'modified', 'moved', 'duration_changed', 'header', 'reset']}
            
            # ヘッダー
            output.append(f"{colors['header']}=== ICSイベント意味的差分 ==={colors['reset']}")
            
            # ファイル情報
            file1_info = diff_data['file1_info']
            file2_info = diff_data['file2_info']
            
            output.append(f"ファイル1: {Path(file1_info['filepath']).name} ({file1_info['events']}イベント)")
            output.append(f"ファイル2: {Path(file2_info['filepath']).name} ({file2_info['events']}イベント)")
            
            # 変更統計
            statistics = diff_data['statistics']
            output.append(f"\n{colors['header']}=== 変更統計 ==={colors['reset']}")
            output.append(f"{colors['added']}+ 追加: {statistics['added']} イベント{colors['reset']}")
            output.append(f"{colors['deleted']}- 削除: {statistics['deleted']} イベント{colors['reset']}")
            output.append(f"{colors['modified']}~ 変更: {statistics['modified']} イベント{colors['reset']}")
            output.append(f"{colors['moved']}= 移動: {statistics['moved']} イベント{colors['reset']}")
            output.append(f"{colors['duration_changed']}Δ 期間変更: {statistics['duration_changed']} イベント{colors['reset']}")
            
            # 詳細差分（日付順）
            sorted_changes = diff_data['sorted_changes']
            if sorted_changes:
                output.append(f"\n{colors['header']}=== 詳細差分（日付順） ==={colors['reset']}")
                
                for change_item in sorted_changes:
                    change_type = change_item['change_type']
                    change_data = change_item['change_data']
                    
                    # 変更種別記号
                    symbols = {
                        'added': '+',
                        'deleted': '-',
                        'modified': '~',
                        'moved': '=',
                        'duration_changed': 'Δ'
                    }
                    
                    symbol = symbols.get(change_type, '?')
                    color = colors.get(change_type, '')
                    
                    # イベント情報取得
                    if change_type in ['added', 'deleted']:
                        event = change_data['event']
                        event_date = event.get('dtstart')
                        event_name = event.get('summary', 'Unknown Event')
                        event_uid = event.get('uid', 'No UID')
                        event_desc = event.get('description', '')
                        
                        # 期間情報
                        if event.get('dtend'):
                            period = f"{event_date.strftime('%Y-%m-%d %H:%M') if event_date else 'N/A'} - {event['dtend'].strftime('%Y-%m-%d %H:%M')}"
                        else:
                            period = f"{event_date.strftime('%Y-%m-%d %H:%M') if event_date else 'N/A'}"
                        
                        # 出力
                        output.append(f"\n{color}{symbol} [{change_type.upper()}] {event_date.strftime('%Y-%m-%d') if event_date else 'N/A'} {event_name}{colors['reset']}")
                        output.append(f"  UID: {event_uid}")
                        output.append(f"  期間: {period}")
                        if event_desc:
                            output.append(f"  説明: {event_desc}")
                    
                    else:
                        # modified, moved, duration_changed
                        event1 = change_data['event1']
                        event2 = change_data['event2']
                        event_date = event2.get('dtstart')
                        event_name = event2.get('summary', 'Unknown Event')
                        event_uid = event2.get('uid', 'No UID')
                        
                        output.append(f"\n{color}{symbol} [{change_type.upper()}] {event_date.strftime('%Y-%m-%d') if event_date else 'N/A'} {event_name}{colors['reset']}")
                        output.append(f"  UID: {event_uid}")
                        
                        # 変更詳細
                        changes_list = change_data.get('changes', [])
                        for prop_change in changes_list:
                            prop = prop_change['property']
                            old_val = prop_change['old_value']
                            new_val = prop_change['new_value']
                            output.append(f"  - {prop}: {old_val} → {new_val}")
            
            else:
                output.append(f"\n{colors['header']}イベントに差分はありません{colors['reset']}")
            
            return '\n'.join(output)
            
        except Exception as e:
            return f"意味的Diff出力フォーマットエラー: {e}"
    
    def export_semantic_diff_file(self, diff_content: str, output_path: str) -> bool:
        """意味的Diff結果ファイル出力.
        
        要件4.2: diff形式出力をファイルに保存
        
        Args:
            diff_content: diff内容文字列
            output_path: 出力ファイルパス
            
        Returns:
            出力成功フラグ
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(diff_content)
            
            self.logger.info(f"意味的Diff結果ファイル出力完了: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"意味的Diff結果ファイル出力失敗: {e}")
            return False
    
    def compare_with_aws_change_calendar(self, local_file: str, calendar_name: str, region: str = 'us-east-1') -> Dict:
        """AWS Change Calendarとの比較.
        
        要件4.3: AWS Change Calendar統合比較
        
        Args:
            local_file: ローカルICSファイルパス
            calendar_name: AWS Change Calendar名
            region: AWSリージョン
            
        Returns:
            AWS比較結果辞書
            
        Raises:
            ICSAnalysisError: AWS比較エラー
        """
        try:
            self.logger.info(f"AWS Change Calendar比較開始: {local_file} vs {calendar_name} ({region})")
            
            # ローカルファイル解析
            local_analysis = self.parse_ics_file(local_file)
            local_events = local_analysis['events']
            
            # AWS Change Calendar取得
            aws_calendar_data = self.fetch_aws_change_calendar(calendar_name, region)
            aws_events = aws_calendar_data['events']
            
            # Change Calendar状態取得
            calendar_state = self.get_change_calendar_state(calendar_name, region)
            
            # 詳細なイベント変更検出（AWS用）
            changes = self.detect_event_changes_detailed(local_events, aws_events)
            
            # AWS比較統計情報計算
            statistics = {
                'local_only': len(changes['added']),      # ローカルにのみ存在
                'aws_only': len(changes['deleted']),      # AWSにのみ存在
                'different': len(changes['modified']),    # 差異あり
                'moved': len(changes['moved']),           # 移動
                'identical': len(local_events) + len(aws_events) - len(changes['added']) - len(changes['deleted']) - len(changes['modified']) - len(changes['moved'])
            }
            
            # 推奨アクション生成
            recommendations = self._generate_aws_recommendations(changes, statistics)
            
            # AWS比較結果構築
            aws_comparison_result = {
                'local_file_info': {
                    'filepath': local_file,
                    'events': len(local_events)
                },
                'aws_calendar_info': {
                    'name': calendar_name,
                    'region': region,
                    'events': len(aws_events),
                    'state': calendar_state,
                    'last_updated': aws_calendar_data.get('last_updated', 'Unknown')
                },
                'comparison_statistics': statistics,
                'differences': {
                    'local_only': changes['added'],
                    'aws_only': changes['deleted'],
                    'different': changes['modified'],
                    'moved': changes['moved']
                },
                'recommendations': recommendations,
                'comparison_date': datetime.now().isoformat()
            }
            
            self.logger.info(f"AWS Change Calendar比較完了: ローカルのみ{statistics['local_only']}件, AWSのみ{statistics['aws_only']}件, 差異{statistics['different']}件")
            
            return aws_comparison_result
            
        except Exception as e:
            if isinstance(e, ICSAnalysisError):
                raise
            else:
                raise ICSAnalysisError(f"AWS Change Calendar比較失敗: {e}")
    
    def fetch_aws_change_calendar(self, calendar_name: str, region: str = 'us-east-1') -> Dict:
        """AWS Change Calendar取得.
        
        要件4.3: AWS Change Calendar取得
        
        Args:
            calendar_name: Change Calendar名
            region: AWSリージョン
            
        Returns:
            AWS Change Calendar辞書
            
        Raises:
            ICSAnalysisError: AWS取得エラー
        """
        try:
            import boto3
            from botocore.exceptions import ClientError, NoCredentialsError
            
            self.logger.info(f"AWS Change Calendar取得開始: {calendar_name} ({region})")
            
            # SSMクライアント作成
            ssm_client = boto3.client('ssm', region_name=region)
            
            # Change Calendarドキュメント取得
            response = ssm_client.get_document(
                Name=calendar_name,
                DocumentFormat='JSON'
            )
            
            # ドキュメント内容解析
            document_content = response['Content']
            
            # AWS Change Calendar → ICS形式正規化
            normalized_events = self.normalize_aws_calendar_to_ics(document_content)
            
            aws_calendar_data = {
                'name': calendar_name,
                'region': region,
                'events': normalized_events,
                'document_version': response.get('DocumentVersion', 'Unknown'),
                'last_updated': response.get('CreatedDate', datetime.now()).isoformat() if response.get('CreatedDate') else datetime.now().isoformat()
            }
            
            self.logger.info(f"AWS Change Calendar取得完了: {calendar_name} ({len(normalized_events)} イベント)")
            
            return aws_calendar_data
            
        except NoCredentialsError:
            raise ICSAnalysisError("AWS認証情報が設定されていません。AWS CLIまたは環境変数を設定してください。")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDenied':
                raise ICSAnalysisError("AWS Change Calendarへのアクセス権限がありません。IAM権限を確認してください。")
            elif error_code == 'DocumentNotFound':
                raise ICSAnalysisError(f"指定されたChange Calendar '{calendar_name}' が見つかりません。カレンダー名を確認してください。")
            else:
                raise ICSAnalysisError(f"AWS API エラー: {e}")
        except ImportError:
            raise ICSAnalysisError("boto3ライブラリがインストールされていません。'pip install boto3'を実行してください。")
        except Exception as e:
            raise ICSAnalysisError(f"AWS Change Calendar取得失敗: {e}")
    
    def normalize_aws_calendar_to_ics(self, aws_calendar_data: str) -> List[Dict]:
        """AWS Change Calendar → ICS形式正規化.
        
        要件4.3: データ正規化
        
        Args:
            aws_calendar_data: AWS Change Calendar JSON文字列
            
        Returns:
            ICS形式イベントリスト
        """
        try:
            import json
            import uuid
            
            normalized_events = []
            
            # AWS Change Calendar JSON解析
            calendar_data = json.loads(aws_calendar_data)
            
            # イベント抽出・変換
            events = calendar_data.get('events', [])
            if not events:
                # 古い形式のChange Calendarの場合
                # 基本的なスケジュール情報から推測
                schedule = calendar_data.get('schedule', {})
                if schedule:
                    # スケジュールからイベント生成（簡易実装）
                    for period in schedule.get('periods', []):
                        start_time = period.get('start')
                        end_time = period.get('end')
                        
                        if start_time and end_time:
                            normalized_event = {
                                'uid': f"aws-change-calendar-{uuid.uuid4()}",
                                'summary': f"AWS Change Calendar: {calendar_data.get('name', 'Unknown')}",
                                'dtstart': self._parse_aws_datetime(start_time),
                                'dtend': self._parse_aws_datetime(end_time),
                                'description': f"AWS Change Calendar period: {period.get('description', '')}",
                                'categories': 'AWS-Change-Calendar'
                            }
                            normalized_events.append(normalized_event)
            else:
                # 標準的なイベント形式
                for event in events:
                    normalized_event = {
                        'uid': event.get('id', f"aws-change-calendar-{uuid.uuid4()}"),
                        'summary': event.get('summary', 'AWS Change Calendar Event'),
                        'dtstart': self._parse_aws_datetime(event.get('start')),
                        'dtend': self._parse_aws_datetime(event.get('end')),
                        'description': event.get('description', ''),
                        'categories': 'AWS-Change-Calendar'
                    }
                    normalized_events.append(normalized_event)
            
            self.logger.info(f"AWS Change Calendar正規化完了: {len(normalized_events)} イベント")
            
            return normalized_events
            
        except json.JSONDecodeError as e:
            raise ICSAnalysisError(f"AWS Change Calendar JSON解析失敗: {e}")
        except Exception as e:
            raise ICSAnalysisError(f"AWS Change Calendar正規化失敗: {e}")
    
    def _parse_aws_datetime(self, aws_datetime_str: str) -> datetime:
        """AWS日時文字列解析.
        
        Args:
            aws_datetime_str: AWS日時文字列
            
        Returns:
            datetimeオブジェクト
        """
        try:
            if not aws_datetime_str:
                return None
            
            # 複数のAWS日時形式に対応
            formats = [
                '%Y-%m-%dT%H:%M:%SZ',           # ISO8601 UTC
                '%Y-%m-%dT%H:%M:%S.%fZ',        # ISO8601 UTC with microseconds
                '%Y-%m-%d',                     # Date only
                '%Y-%m-%dT%H:%M:%S',            # ISO8601 without timezone
                '%Y/%m/%d %H:%M:%S',            # Alternative format
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(aws_datetime_str, fmt)
                except ValueError:
                    continue
            
            # フォールバック: dateutil.parser使用
            try:
                from dateutil import parser
                return parser.parse(aws_datetime_str)
            except ImportError:
                pass
            
            self.logger.warning(f"AWS日時解析失敗: {aws_datetime_str}")
            return None
            
        except Exception as e:
            self.logger.warning(f"AWS日時解析エラー: {e}")
            return None
    
    def get_change_calendar_state(self, calendar_name: str, region: str = 'us-east-1') -> str:
        """Change Calendar状態取得.
        
        要件4.3: Change Calendar状態取得
        
        Args:
            calendar_name: Change Calendar名
            region: AWSリージョン
            
        Returns:
            カレンダー状態 ('OPEN' or 'CLOSED')
        """
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            # SSMクライアント作成
            ssm_client = boto3.client('ssm', region_name=region)
            
            # カレンダー状態取得
            response = ssm_client.get_calendar_state(
                CalendarNames=[calendar_name]
            )
            
            # 状態抽出
            if response.get('State'):
                return response['State']
            else:
                return 'UNKNOWN'
                
        except ClientError as e:
            self.logger.warning(f"Change Calendar状態取得失敗: {e}")
            return 'UNKNOWN'
        except Exception as e:
            self.logger.warning(f"Change Calendar状態取得エラー: {e}")
            return 'UNKNOWN'
    
    def _generate_aws_recommendations(self, changes: Dict, statistics: Dict) -> List[str]:
        """AWS推奨アクション生成.
        
        Args:
            changes: 変更辞書
            statistics: 統計辞書
            
        Returns:
            推奨アクションリスト
        """
        recommendations = []
        
        # ローカルのみのイベント
        if statistics['local_only'] > 0:
            recommendations.append(f"{statistics['local_only']}件のローカルイベントをAWS Change Calendarに追加することを推奨します")
        
        # AWSのみのイベント
        if statistics['aws_only'] > 0:
            recommendations.append(f"{statistics['aws_only']}件のAWSイベントがローカルファイルに不足しています")
        
        # 差異のあるイベント
        if statistics['different'] > 0:
            recommendations.append(f"{statistics['different']}件のイベントに差異があります。内容を確認してください")
        
        # 移動されたイベント
        if statistics['moved'] > 0:
            recommendations.append(f"{statistics['moved']}件のイベントが移動されています。日時を確認してください")
        
        # 全体的な推奨
        if statistics['local_only'] == 0 and statistics['aws_only'] == 0 and statistics['different'] == 0:
            recommendations.append("ローカルファイルとAWS Change Calendarは同期されています")
        else:
            recommendations.append("AWS Change Calendarの更新後、状態確認を実施してください")
            recommendations.append("次回比較: 1ヶ月後（推奨）")
        
        return recommendations
    
    def format_aws_comparison_result(self, comparison: Dict, use_color: bool = False) -> str:
        """AWS比較結果フォーマット.
        
        要件4.3: AWS専用出力フォーマット
        
        Args:
            comparison: AWS比較結果辞書
            use_color: カラー出力使用フラグ
            
        Returns:
            フォーマットされたAWS比較結果文字列
        """
        try:
            output = []
            
            # カラーコード定義
            colors = {
                'local_only': '\033[32m',     # Green (+)
                'aws_only': '\033[31m',       # Red (-)
                'different': '\033[33m',      # Yellow (~)
                'moved': '\033[34m',          # Blue (=)
                'header': '\033[1m',          # Bold
                'reset': '\033[0m'            # Reset
            } if use_color else {key: '' for key in ['local_only', 'aws_only', 'different', 'moved', 'header', 'reset']}
            
            # ヘッダー
            output.append(f"{colors['header']}=== AWS Change Calendar比較結果 ==={colors['reset']}")
            
            # ファイル・カレンダー情報
            local_info = comparison['local_file_info']
            aws_info = comparison['aws_calendar_info']
            
            output.append(f"ローカルファイル: {Path(local_info['filepath']).name} ({local_info['events']}イベント)")
            output.append(f"AWS Change Calendar: {aws_info['name']} ({aws_info['events']}イベント, 状態: {aws_info['state']})")
            output.append(f"リージョン: {aws_info['region']}")
            
            # 変更統計
            statistics = comparison['comparison_statistics']
            output.append(f"\n{colors['header']}=== 変更統計 ==={colors['reset']}")
            output.append(f"{colors['local_only']}+ ローカルのみ: {statistics['local_only']} イベント{colors['reset']}")
            output.append(f"{colors['aws_only']}- AWSのみ: {statistics['aws_only']} イベント{colors['reset']}")
            output.append(f"{colors['different']}~ 差異: {statistics['different']} イベント{colors['reset']}")
            output.append(f"{colors['moved']}= 移動: {statistics['moved']} イベント{colors['reset']}")
            
            # 詳細差分
            differences = comparison['differences']
            
            if any([differences['local_only'], differences['aws_only'], differences['different'], differences['moved']]):
                output.append(f"\n{colors['header']}=== 詳細差分（日付順） ==={colors['reset']}")
                
                # 全ての差分を日付順にソート
                all_diffs = []
                
                # ローカルのみ
                for item in differences['local_only']:
                    event = item['event']
                    all_diffs.append({
                        'type': 'local_only',
                        'date': event.get('dtstart', datetime.min),
                        'event': event,
                        'symbol': '+',
                        'label': 'ローカルのみ'
                    })
                
                # AWSのみ
                for item in differences['aws_only']:
                    event = item['event']
                    all_diffs.append({
                        'type': 'aws_only',
                        'date': event.get('dtstart', datetime.min),
                        'event': event,
                        'symbol': '-',
                        'label': 'AWSのみ'
                    })
                
                # 差異
                for item in differences['different']:
                    event = item['event2']
                    all_diffs.append({
                        'type': 'different',
                        'date': event.get('dtstart', datetime.min),
                        'event': event,
                        'symbol': '~',
                        'label': '差異',
                        'changes': item.get('changes', [])
                    })
                
                # 移動
                for item in differences['moved']:
                    event = item['event2']
                    all_diffs.append({
                        'type': 'moved',
                        'date': event.get('dtstart', datetime.min),
                        'event': event,
                        'symbol': '=',
                        'label': '移動',
                        'changes': item.get('changes', [])
                    })
                
                # 日付順ソート
                all_diffs.sort(key=lambda x: x['date'] if x['date'] else datetime.min)
                
                # 差分出力
                for diff in all_diffs:
                    event = diff['event']
                    event_date = event.get('dtstart')
                    event_name = event.get('summary', 'Unknown Event')
                    event_uid = event.get('uid', 'No UID')
                    
                    color = colors.get(diff['type'], '')
                    symbol = diff['symbol']
                    label = diff['label']
                    
                    output.append(f"\n{color}{symbol} [{label}] {event_date.strftime('%Y-%m-%d') if event_date else 'N/A'} {event_name}{colors['reset']}")
                    output.append(f"  UID: {event_uid}")
                    
                    if event.get('dtend'):
                        period = f"{event_date.strftime('%Y-%m-%d %H:%M') if event_date else 'N/A'} - {event['dtend'].strftime('%Y-%m-%d %H:%M')}"
                        output.append(f"  期間: {period}")
                    
                    if event.get('description'):
                        output.append(f"  説明: {event['description']}")
                    
                    # 推奨アクション
                    if diff['type'] == 'local_only':
                        output.append(f"  → AWS Change Calendarに追加推奨")
                    elif diff['type'] == 'aws_only':
                        output.append(f"  → ローカルファイルに追加検討")
                    
                    # 変更詳細
                    if 'changes' in diff:
                        for change in diff['changes']:
                            prop = change['property']
                            old_val = change['old_value']
                            new_val = change['new_value']
                            output.append(f"  - {prop}: {old_val} → {new_val}")
            
            else:
                output.append(f"\n{colors['header']}差分はありません（ローカルファイルとAWS Change Calendarは同期されています）{colors['reset']}")
            
            # 推奨アクション
            recommendations = comparison['recommendations']
            if recommendations:
                output.append(f"\n{colors['header']}=== 推奨アクション ==={colors['reset']}")
                for i, rec in enumerate(recommendations, 1):
                    output.append(f"{i}. {rec}")
            
            return '\n'.join(output)
            
        except Exception as e:
            return f"AWS比較結果フォーマットエラー: {e}"