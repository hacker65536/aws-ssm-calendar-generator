"""
Unit tests for CalendarAnalyzer class.
Tests requirement 3: ICSファイル解析・可視化
Tests requirement 4: ICSファイル比較・差分表示
"""

import pytest
from unittest.mock import Mock, patch
from datetime import date, datetime
import tempfile
import json

from src.calendar_analyzer import ICSAnalyzer, ICSAnalysisError


class TestICSAnalyzer:
    """Test cases for ICSAnalyzer class."""

    def test_init(self):
        """Test analyzer initialization."""
        analyzer = ICSAnalyzer()
        assert analyzer is not None

    def test_parse_ics_file_valid(self, temp_dir, sample_ics_content):
        """Test parsing valid ICS file."""
        # Create test ICS file
        ics_file = temp_dir / "test.ics"
        ics_file.write_text(sample_ics_content, encoding='utf-8')
        
        analyzer = ICSAnalyzer()
        result = analyzer.parse_ics_file(str(ics_file))
        
        assert 'file_info' in result
        assert 'events' in result
        assert 'statistics' in result
        assert result['file_info']['total_events'] > 0

    def test_parse_ics_file_invalid(self, temp_dir):
        """Test parsing invalid ICS file."""
        # Create invalid ICS file
        ics_file = temp_dir / "invalid.ics"
        ics_file.write_text("INVALID ICS CONTENT", encoding='utf-8')
        
        analyzer = ICSAnalyzer()
        
        with pytest.raises(ICSAnalysisError):
            analyzer.parse_ics_file(str(ics_file))

    def test_parse_ics_file_not_found(self):
        """Test parsing non-existent ICS file."""
        analyzer = ICSAnalyzer()
        
        with pytest.raises(ICSAnalysisError):
            analyzer.parse_ics_file("non_existent_file.ics")

    def test_extract_events(self, temp_dir, sample_ics_content):
        """Test extracting events from ICS calendar."""
        ics_file = temp_dir / "test.ics"
        ics_file.write_text(sample_ics_content, encoding='utf-8')
        
        analyzer = ICSAnalyzer()
        result = analyzer.parse_ics_file(str(ics_file))
        events = result['events']
        
        assert len(events) > 0
        
        # Check event structure
        event = events[0]
        assert 'uid' in event
        assert 'summary' in event
        assert 'dtstart' in event
        assert 'dtend' in event

    def test_analyze_events(self, temp_dir, sample_ics_content):
        """Test event analysis and statistics generation."""
        ics_file = temp_dir / "test.ics"
        ics_file.write_text(sample_ics_content, encoding='utf-8')
        
        analyzer = ICSAnalyzer()
        result = analyzer.parse_ics_file(str(ics_file))
        
        stats = result['statistics']
        assert 'total_events' in stats
        assert 'holiday_types' in stats
        assert 'yearly_distribution' in stats
        assert 'monthly_distribution' in stats

    def test_format_human_readable(self, temp_dir, sample_ics_content):
        """Test human-readable format output."""
        ics_file = temp_dir / "test.ics"
        ics_file.write_text(sample_ics_content, encoding='utf-8')
        
        analyzer = ICSAnalyzer()
        result = analyzer.parse_ics_file(str(ics_file))
        
        human_readable = analyzer.format_human_readable(result)
        
        assert isinstance(human_readable, str)
        assert "ICSファイル解析結果" in human_readable
        assert "総イベント数" in human_readable
        assert "元日" in human_readable

    def test_export_json(self, temp_dir, sample_ics_content):
        """Test JSON format export."""
        ics_file = temp_dir / "test.ics"
        ics_file.write_text(sample_ics_content, encoding='utf-8')
        
        analyzer = ICSAnalyzer()
        result = analyzer.parse_ics_file(str(ics_file))
        
        json_output = analyzer.export_json(result)
        
        # Verify it's valid JSON
        parsed_json = json.loads(json_output)
        assert 'file_info' in parsed_json
        assert 'events' in parsed_json
        assert 'statistics' in parsed_json

    def test_export_csv(self, temp_dir, sample_ics_content):
        """Test CSV format export."""
        ics_file = temp_dir / "test.ics"
        ics_file.write_text(sample_ics_content, encoding='utf-8')
        
        analyzer = ICSAnalyzer()
        result = analyzer.parse_ics_file(str(ics_file))
        
        csv_output = analyzer.export_csv(result['events'])
        
        assert isinstance(csv_output, str)
        assert "日付,祝日名,説明,カテゴリ,UID" in csv_output
        assert "jp-holiday-20240101" in csv_output

    def test_validate_ics_format(self, temp_dir, sample_ics_content):
        """Test ICS format validation."""
        ics_file = temp_dir / "test.ics"
        ics_file.write_text(sample_ics_content, encoding='utf-8')
        
        analyzer = ICSAnalyzer()
        result = analyzer.parse_ics_file(str(ics_file))
        
        errors = result.get('validation_errors', [])
        assert isinstance(errors, list)
        # Valid ICS should have no errors
        assert len(errors) == 0

    def test_compare_ics_files(self, temp_dir, sample_ics_content):
        """Test comparing two ICS files."""
        # Create two test ICS files
        ics_file1 = temp_dir / "test1.ics"
        ics_file1.write_text(sample_ics_content, encoding='utf-8')
        
        # Create modified version
        modified_content = sample_ics_content.replace("元日", "New Year's Day")
        ics_file2 = temp_dir / "test2.ics"
        ics_file2.write_text(modified_content, encoding='utf-8')
        
        analyzer = ICSAnalyzer()
        comparison = analyzer.compare_ics_files(str(ics_file1), str(ics_file2))
        
        assert 'file1_info' in comparison
        assert 'file2_info' in comparison
        assert 'summary' in comparison
        assert 'changes' in comparison

    def test_detect_event_changes(self, temp_dir):
        """Test detecting changes between event lists."""
        analyzer = ICSAnalyzer()
        
        events1 = [
            {
                'uid': 'test-1',
                'summary': 'Event 1',
                'dtstart': datetime(2024, 1, 1),
                'dtend': datetime(2024, 1, 2)
            }
        ]
        
        events2 = [
            {
                'uid': 'test-1',
                'summary': 'Modified Event 1',
                'dtstart': datetime(2024, 1, 1),
                'dtend': datetime(2024, 1, 2)
            },
            {
                'uid': 'test-2',
                'summary': 'New Event',
                'dtstart': datetime(2024, 1, 3),
                'dtend': datetime(2024, 1, 4)
            }
        ]
        
        changes = analyzer.detect_event_changes(events1, events2)
        
        assert 'added' in changes
        assert 'deleted' in changes
        assert 'modified' in changes
        assert len(changes['added']) == 1
        assert len(changes['modified']) == 1

    def test_format_comparison_result(self, temp_dir):
        """Test formatting comparison results."""
        analyzer = ICSAnalyzer()
        
        comparison = {
            'file1_info': {'filepath': 'test1.ics', 'total_events': 1},
            'file2_info': {'filepath': 'test2.ics', 'total_events': 2},
            'summary': {'added': 1, 'deleted': 0, 'modified': 1, 'unchanged': 0},
            'changes': {
                'added': [{'event': {'uid': 'test-2', 'summary': 'New Event', 'dtstart': datetime(2024, 1, 1)}}],
                'deleted': [],
                'modified': [{'event2': {'uid': 'test-1', 'summary': 'Modified Event', 'dtstart': datetime(2024, 1, 1)}, 'property_changes': ['SUMMARY: Original → Modified']}]
            }
        }
        
        formatted = analyzer.format_comparison_result(comparison)
        
        assert isinstance(formatted, str)
        assert "ICSファイル比較結果" in formatted
        assert "追加: 1件" in formatted
        assert "変更: 1件" in formatted

    def test_generate_event_semantic_diff(self, temp_dir, sample_ics_content):
        """Test generating semantic diff between events."""
        # Create two test ICS files with different content
        ics_file1 = temp_dir / "test1.ics"
        ics_file1.write_text(sample_ics_content, encoding='utf-8')
        
        # Create modified version with different event
        modified_content = sample_ics_content.replace(
            "DTSTART;TZID=Asia/Tokyo:20240101T000000",
            "DTSTART;TZID=Asia/Tokyo:20240102T000000"
        )
        ics_file2 = temp_dir / "test2.ics"
        ics_file2.write_text(modified_content, encoding='utf-8')
        
        analyzer = ICSAnalyzer()
        diff_result = analyzer.generate_event_semantic_diff(str(ics_file1), str(ics_file2))
        
        assert 'statistics' in diff_result
        assert 'changes' in diff_result
        assert 'sorted_changes' in diff_result

    def test_classify_event_changes(self, temp_dir):
        """Test classifying different types of event changes."""
        analyzer = ICSAnalyzer()
        
        # Test moved event (different start time)
        event1 = {
            'uid': 'test-1',
            'summary': 'Event 1',
            'dtstart': datetime(2024, 1, 1),
            'dtend': datetime(2024, 1, 2),
            'description': 'Test event',
            'categories': 'Test'
        }
        
        event2_moved = {
            'uid': 'test-1',
            'summary': 'Event 1',
            'dtstart': datetime(2024, 1, 2),  # Different start time
            'dtend': datetime(2024, 1, 3),    # Same duration
            'description': 'Test event',
            'categories': 'Test'
        }
        
        change_type = analyzer.classify_event_changes(event1, event2_moved)
        assert change_type == 'moved'
        
        # Test modified event (different summary)
        event2_modified = {
            'uid': 'test-1',
            'summary': 'Modified Event 1',  # Different summary
            'dtstart': datetime(2024, 1, 1),
            'dtend': datetime(2024, 1, 2),
            'description': 'Test event',
            'categories': 'Test'
        }
        
        change_type = analyzer.classify_event_changes(event1, event2_modified)
        assert change_type == 'modified'

    def test_format_semantic_diff(self, temp_dir):
        """Test formatting semantic diff output."""
        analyzer = ICSAnalyzer()
        
        diff_data = {
            'file1_info': {'filepath': 'test1.ics', 'events': 1},
            'file2_info': {'filepath': 'test2.ics', 'events': 1},
            'statistics': {
                'added': 0,
                'deleted': 0,
                'modified': 1,
                'moved': 0,
                'duration_changed': 0,
                'unchanged': 0
            },
            'sorted_changes': [
                {
                    'change_type': 'modified',
                    'sort_date': datetime(2024, 1, 1),
                    'change_data': {
                        'uid': 'test-1',
                        'event1': {'summary': 'Original Event', 'dtstart': datetime(2024, 1, 1)},
                        'event2': {'summary': 'Modified Event', 'dtstart': datetime(2024, 1, 1)},
                        'changes': [{'property': 'summary', 'old_value': 'Original Event', 'new_value': 'Modified Event'}]
                    }
                }
            ]
        }
        
        formatted = analyzer.format_semantic_diff(diff_data)
        
        assert isinstance(formatted, str)
        assert "ICSイベント意味的差分" in formatted
        assert "変更統計" in formatted
        assert "詳細差分" in formatted

    @patch('boto3.client')
    def test_compare_with_aws_change_calendar(self, mock_boto_client, temp_dir, sample_ics_content):
        """Test comparing with AWS Change Calendar."""
        # Mock AWS client
        mock_client = Mock()
        mock_client.get_document.return_value = {
            'Content': json.dumps({
                'events': [
                    {
                        'id': 'test-event',
                        'summary': 'AWS Event',
                        'start': '2024-01-01T00:00:00Z',
                        'end': '2024-01-02T00:00:00Z'
                    }
                ]
            })
        }
        mock_boto_client.return_value = mock_client
        
        # Create local ICS file
        ics_file = temp_dir / "test.ics"
        ics_file.write_text(sample_ics_content, encoding='utf-8')
        
        analyzer = ICSAnalyzer()
        comparison = analyzer.compare_with_aws_change_calendar(
            str(ics_file), 
            'test-calendar'
        )
        
        assert 'local_file_info' in comparison
        assert 'aws_calendar_info' in comparison


class TestSemanticDiff:
    """Test cases for semantic diff functionality (要件4.2)."""

    def test_event_matching_algorithm_accuracy(self, temp_dir):
        """Test event matching algorithm precision with UID primary key matching."""
        analyzer = ICSAnalyzer()
        
        # Create test events with various matching scenarios
        events1 = [
            {
                'uid': 'event-1',
                'summary': 'New Year',
                'dtstart': datetime(2024, 1, 1),
                'dtend': datetime(2024, 1, 2),
                'description': 'National Holiday',
                'categories': 'Japanese-Holiday'
            },
            {
                'uid': 'event-2',
                'summary': 'Coming of Age Day',
                'dtstart': datetime(2024, 1, 8),
                'dtend': datetime(2024, 1, 9),
                'description': 'National Holiday',
                'categories': 'Japanese-Holiday'
            },
            {
                'uid': '',  # No UID - should use DTSTART/SUMMARY fallback
                'summary': 'Constitution Day',
                'dtstart': datetime(2024, 5, 3),
                'dtend': datetime(2024, 5, 4),
                'description': 'National Holiday',
                'categories': 'Japanese-Holiday'
            }
        ]
        
        events2 = [
            {
                'uid': 'event-1',  # Same UID, modified content
                'summary': 'New Year (Modified)',
                'dtstart': datetime(2024, 1, 1),
                'dtend': datetime(2024, 1, 2),
                'description': 'National Holiday - Modified',
                'categories': 'Japanese-Holiday'
            },
            {
                'uid': 'event-3',  # New event
                'summary': 'Golden Week',
                'dtstart': datetime(2024, 4, 29),
                'dtend': datetime(2024, 4, 30),
                'description': 'National Holiday',
                'categories': 'Japanese-Holiday'
            },
            {
                'uid': '',  # No UID - same DTSTART/SUMMARY as events1
                'summary': 'Constitution Day',
                'dtstart': datetime(2024, 5, 3),
                'dtend': datetime(2024, 5, 4),
                'description': 'National Holiday',
                'categories': 'Japanese-Holiday'
            }
        ]
        
        changes = analyzer.detect_event_changes_detailed(events1, events2)
        
        # Verify UID-based matching accuracy
        assert len(changes['added']) == 1  # event-3 added
        assert len(changes['deleted']) == 1  # event-2 deleted
        assert len(changes['modified']) == 1  # event-1 modified
        
        # Verify correct event identification
        added_event = changes['added'][0]
        assert added_event['uid'] == 'event-3'
        assert added_event['event']['summary'] == 'Golden Week'
        
        deleted_event = changes['deleted'][0]
        assert deleted_event['uid'] == 'event-2'
        assert deleted_event['event']['summary'] == 'Coming of Age Day'
        
        modified_event = changes['modified'][0]
        assert modified_event['uid'] == 'event-1'
        assert modified_event['event2']['summary'] == 'New Year (Modified)'

    def test_change_classification_accuracy(self, temp_dir):
        """Test change classification and statistics generation."""
        analyzer = ICSAnalyzer()
        
        # Test different types of changes
        base_event = {
            'uid': 'test-event',
            'summary': 'Test Event',
            'dtstart': datetime(2024, 1, 1, 9, 0),
            'dtend': datetime(2024, 1, 1, 17, 0),
            'description': 'Original description',
            'categories': 'Test'
        }
        
        # Test 1: Modified event (summary change)
        modified_event = base_event.copy()
        modified_event['summary'] = 'Modified Test Event'
        
        change_type = analyzer.classify_event_changes(base_event, modified_event)
        assert change_type == 'modified'
        
        # Test 2: Moved event (same duration, different time)
        moved_event = base_event.copy()
        moved_event['dtstart'] = datetime(2024, 1, 2, 9, 0)
        moved_event['dtend'] = datetime(2024, 1, 2, 17, 0)
        
        change_type = analyzer.classify_event_changes(base_event, moved_event)
        assert change_type == 'moved'
        
        # Test 3: Duration changed event
        duration_changed_event = base_event.copy()
        duration_changed_event['dtend'] = datetime(2024, 1, 1, 18, 0)  # 1 hour longer
        
        change_type = analyzer.classify_event_changes(base_event, duration_changed_event)
        assert change_type == 'duration_changed'
        
        # Test 4: Unchanged event
        unchanged_event = base_event.copy()
        
        change_type = analyzer.classify_event_changes(base_event, unchanged_event)
        assert change_type == 'unchanged'

    def test_detailed_property_changes(self, temp_dir):
        """Test detailed property change detection."""
        analyzer = ICSAnalyzer()
        
        event1 = {
            'uid': 'test-event',
            'summary': 'Original Event',
            'dtstart': datetime(2024, 1, 1, 9, 0),
            'dtend': datetime(2024, 1, 1, 17, 0),
            'description': 'Original description',
            'categories': 'Original'
        }
        
        event2 = {
            'uid': 'test-event',
            'summary': 'Modified Event',
            'dtstart': datetime(2024, 1, 2, 9, 0),
            'dtend': datetime(2024, 1, 2, 18, 0),
            'description': 'Modified description',
            'categories': 'Modified'
        }
        
        changes = analyzer._get_detailed_property_changes(event1, event2)
        
        # Verify all changed properties are detected
        changed_props = [change['property'] for change in changes]
        assert 'summary' in changed_props
        assert 'dtstart' in changed_props
        assert 'dtend' in changed_props
        assert 'description' in changed_props
        assert 'categories' in changed_props
        
        # Verify change details
        summary_change = next(c for c in changes if c['property'] == 'summary')
        assert summary_change['old_value'] == 'Original Event'
        assert summary_change['new_value'] == 'Modified Event'
        assert summary_change['change_type'] == 'string'
        
        dtstart_change = next(c for c in changes if c['property'] == 'dtstart')
        assert dtstart_change['change_type'] == 'datetime'
        assert dtstart_change['old_value'] == '2024-01-01T09:00:00'
        assert dtstart_change['new_value'] == '2024-01-02T09:00:00'

    def test_chronological_sorting(self, temp_dir):
        """Test chronological sorting of changes."""
        analyzer = ICSAnalyzer()
        
        # Create changes with different dates (unsorted)
        changes = {
            'added': [
                {
                    'event': {
                        'uid': 'event-3',
                        'summary': 'March Event',
                        'dtstart': datetime(2024, 3, 1)
                    },
                    'change_type': 'added',
                    'uid': 'event-3'
                }
            ],
            'deleted': [
                {
                    'event': {
                        'uid': 'event-1',
                        'summary': 'January Event',
                        'dtstart': datetime(2024, 1, 1)
                    },
                    'change_type': 'deleted',
                    'uid': 'event-1'
                }
            ],
            'modified': [
                {
                    'event1': {
                        'uid': 'event-2',
                        'summary': 'February Event',
                        'dtstart': datetime(2024, 2, 1)
                    },
                    'event2': {
                        'uid': 'event-2',
                        'summary': 'February Event Modified',
                        'dtstart': datetime(2024, 2, 1)
                    },
                    'change_type': 'modified',
                    'uid': 'event-2'
                }
            ],
            'moved': [],
            'duration_changed': []
        }
        
        sorted_changes = analyzer._sort_changes_chronologically(changes)
        
        # Verify chronological order
        assert len(sorted_changes) == 3
        assert sorted_changes[0]['sort_date'] == datetime(2024, 1, 1)  # January
        assert sorted_changes[1]['sort_date'] == datetime(2024, 2, 1)  # February
        assert sorted_changes[2]['sort_date'] == datetime(2024, 3, 1)  # March
        
        # Verify change types are preserved
        assert sorted_changes[0]['change_type'] == 'deleted'
        assert sorted_changes[1]['change_type'] == 'modified'
        assert sorted_changes[2]['change_type'] == 'added'

    def test_semantic_diff_statistics(self, temp_dir, sample_ics_content):
        """Test semantic diff statistics calculation."""
        # Create two ICS files with known differences
        ics_file1 = temp_dir / "test1.ics"
        ics_file1.write_text(sample_ics_content, encoding='utf-8')
        
        # Create modified version with additional event
        # Insert the new event before the END:VCALENDAR
        modified_content = sample_ics_content.replace(
            "END:VCALENDAR",
            """BEGIN:VEVENT
UID:jp-holiday-20240108@aws-ssm-change-calendar
DTSTAMP:20241029T120000Z
DTSTART;TZID=Asia/Tokyo:20240108T000000
DTEND;TZID=Asia/Tokyo:20240109T000000
SUMMARY:日本の祝日: 成人の日
DESCRIPTION:日本の国民の祝日: 成人の日
CATEGORIES:Japanese-Holiday
END:VEVENT

END:VCALENDAR"""
        )
        
        ics_file2 = temp_dir / "test2.ics"
        ics_file2.write_text(modified_content, encoding='utf-8')
        
        analyzer = ICSAnalyzer()
        diff_result = analyzer.generate_event_semantic_diff(str(ics_file1), str(ics_file2))
        
        # Verify statistics structure
        stats = diff_result['statistics']
        assert 'added' in stats
        assert 'deleted' in stats
        assert 'modified' in stats
        assert 'moved' in stats
        assert 'duration_changed' in stats
        assert 'unchanged' in stats
        
        # Verify statistics values
        assert stats['added'] == 1  # One new event added
        assert stats['deleted'] == 0
        assert stats['modified'] == 0
        assert stats['moved'] == 0
        assert stats['duration_changed'] == 0

    def test_color_output_formatting(self, temp_dir):
        """Test color output and formatting."""
        analyzer = ICSAnalyzer()
        
        # Create test diff data
        diff_data = {
            'file1_info': {'filepath': 'test1.ics', 'events': 1},
            'file2_info': {'filepath': 'test2.ics', 'events': 2},
            'statistics': {
                'added': 1,
                'deleted': 0,
                'modified': 0,
                'moved': 0,
                'duration_changed': 0,
                'unchanged': 1
            },
            'sorted_changes': [
                {
                    'change_type': 'added',
                    'sort_date': datetime(2024, 1, 8),
                    'change_data': {
                        'event': {
                            'uid': 'test-event',
                            'summary': 'Test Event',
                            'dtstart': datetime(2024, 1, 8),
                            'dtend': datetime(2024, 1, 9),
                            'description': 'Test description'
                        },
                        'change_type': 'added',
                        'uid': 'test-event'
                    }
                }
            ]
        }
        
        # Test without color
        formatted_no_color = analyzer.format_semantic_diff(diff_data, use_color=False)
        assert 'ICSイベント意味的差分' in formatted_no_color
        assert '+ 追加: 1 イベント' in formatted_no_color
        assert '+ [ADDED] 2024-01-08 Test Event' in formatted_no_color
        assert '\033[' not in formatted_no_color  # No ANSI codes
        
        # Test with color
        formatted_with_color = analyzer.format_semantic_diff(diff_data, use_color=True)
        assert 'ICSイベント意味的差分' in formatted_with_color
        assert '\033[32m+ 追加: 1 イベント\033[0m' in formatted_with_color  # Green color
        assert '\033[32m+ [ADDED]' in formatted_with_color

    def test_semantic_diff_file_export(self, temp_dir):
        """Test semantic diff file export functionality."""
        analyzer = ICSAnalyzer()
        
        diff_content = """=== ICSイベント意味的差分 ===
ファイル1: test1.ics (1イベント)
ファイル2: test2.ics (2イベント)

=== 変更統計 ===
+ 追加: 1 イベント
- 削除: 0 イベント

=== 詳細差分（日付順） ===

+ [ADDED] 2024-01-08 成人の日
  UID: jp-holiday-20240108@aws-ssm-change-calendar
  期間: 2024-01-08 00:00 - 2024-01-09 00:00
"""
        
        output_file = temp_dir / "semantic_diff.txt"
        
        # Test file export
        success = analyzer.export_semantic_diff_file(diff_content, str(output_file))
        
        assert success is True
        assert output_file.exists()
        
        # Verify file content
        saved_content = output_file.read_text(encoding='utf-8')
        assert saved_content == diff_content

    def test_integration_with_existing_comparison_system(self, temp_dir, sample_ics_content):
        """Test integration with existing comparison system."""
        analyzer = ICSAnalyzer()
        
        # Create two test files
        ics_file1 = temp_dir / "test1.ics"
        ics_file1.write_text(sample_ics_content, encoding='utf-8')
        
        # Create modified version
        modified_content = sample_ics_content.replace("元日", "New Year's Day")
        ics_file2 = temp_dir / "test2.ics"
        ics_file2.write_text(modified_content, encoding='utf-8')
        
        # Test traditional comparison
        traditional_comparison = analyzer.compare_ics_files(str(ics_file1), str(ics_file2))
        
        # Test semantic diff comparison
        semantic_diff = analyzer.generate_event_semantic_diff(str(ics_file1), str(ics_file2))
        
        # Verify both methods detect the same change
        assert traditional_comparison['summary']['modified'] == 1
        assert semantic_diff['statistics']['modified'] == 1
        
        # Verify semantic diff provides more detailed information
        assert 'sorted_changes' in semantic_diff
        assert 'changes' in semantic_diff
        assert len(semantic_diff['changes']['modified']) == 1
        
        # Verify detailed change information is available in semantic diff
        modified_change = semantic_diff['changes']['modified'][0]
        assert 'changes' in modified_change
        assert len(modified_change['changes']) > 0
        
        # Verify property-level change detection
        summary_change = next(
            (c for c in modified_change['changes'] if c['property'] == 'summary'), 
            None
        )
        assert summary_change is not None
        assert summary_change['old_value'] == '日本の祝日: 元日'
        assert summary_change['new_value'] == '日本の祝日: New Year\'s Day'

    def test_edge_cases_and_error_handling(self, temp_dir):
        """Test edge cases and error handling in semantic diff."""
        analyzer = ICSAnalyzer()
        
        # Test with empty events lists
        empty_changes = analyzer.detect_event_changes_detailed([], [])
        assert all(len(changes) == 0 for changes in empty_changes.values())
        
        # Test with events missing required fields
        incomplete_event = {
            'uid': 'incomplete',
            'summary': 'Incomplete Event'
            # Missing dtstart, dtend
        }
        
        complete_event = {
            'uid': 'complete',
            'summary': 'Complete Event',
            'dtstart': datetime(2024, 1, 1),
            'dtend': datetime(2024, 1, 2),
            'description': 'Complete description',
            'categories': 'Test'
        }
        
        # Should handle incomplete events gracefully
        changes = analyzer.detect_event_changes_detailed([incomplete_event], [complete_event])
        assert len(changes['added']) == 1
        assert len(changes['deleted']) == 1
        
        # Test chronological sorting with None dates
        changes_with_none = {
            'added': [
                {
                    'event': {'uid': 'no-date'},  # Missing dtstart entirely
                    'change_type': 'added',
                    'uid': 'no-date'
                }
            ],
            'deleted': [],
            'modified': [],
            'moved': [],
            'duration_changed': []
        }
        
        # Should handle missing dates without crashing
        sorted_changes = analyzer._sort_changes_chronologically(changes_with_none)
        assert len(sorted_changes) == 1
        # The sort_date should be datetime.min for events without dtstart (as per implementation)
        assert sorted_changes[0]['sort_date'] == datetime.min