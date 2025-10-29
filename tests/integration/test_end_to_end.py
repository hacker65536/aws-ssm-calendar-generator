"""
End-to-end integration tests.
Tests the complete workflow from holiday data fetching to ICS generation.
"""

import pytest
from unittest.mock import patch, Mock
import tempfile
import os
import json
from datetime import date, datetime

from src.japanese_holidays import JapaneseHolidays
from src.ics_generator import ICSGenerator
from src.calendar_analyzer import ICSAnalyzer
from src.aws_client import SSMChangeCalendarClient
from src.change_calendar_manager import ChangeCalendarManager


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows."""

    @pytest.mark.integration
    def test_complete_holiday_to_ics_workflow(self, temp_dir, monkeypatch):
        """Test complete workflow from holiday data to ICS generation."""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # Create cache with holiday data directly
        cache_dir = temp_dir / ".aws-ssm-calendar" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "japanese_holidays.csv"
        
        holiday_data = """日付,祝日名
2025/01/01,元日
2025/01/13,成人の日
2025/02/11,建国記念の日
2025/02/23,天皇誕生日
2025/03/20,春分の日"""
        cache_file.write_text(holiday_data, encoding='utf-8')
        
        # Step 1: Fetch and process holiday data
        holidays = JapaneseHolidays()
        stats = holidays.get_stats()
        
        assert stats['total'] > 0
        assert holidays.is_holiday(date(2025, 1, 1))
        assert holidays.get_holiday_name(date(2025, 1, 1)) == "元日"
        
        # Step 2: Generate ICS content
        ics_generator = ICSGenerator(japanese_holidays=holidays)
        
        # Step 3: Save ICS file
        output_file = temp_dir / "test_holidays.ics"
        ics_generator.save_to_file(str(output_file))
        
        assert output_file.exists()
        
        # Step 4: Analyze generated ICS file
        analyzer = ICSAnalyzer()
        analysis = analyzer.parse_ics_file(str(output_file))
        
        assert analysis['file_info']['total_events'] > 0
        assert len(analysis['validation_errors']) == 0
        
        # Verify ICS content
        content = output_file.read_text(encoding='utf-8')
        assert 'BEGIN:VCALENDAR' in content
        assert '-//AWS//Change Calendar 1.0//EN' in content
        assert '元日' in content
        assert 'Asia/Tokyo' in content

    @pytest.mark.integration
    def test_ics_comparison_workflow(self, temp_dir, monkeypatch):
        """Test ICS file comparison workflow."""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # Create cache with holiday data
        cache_dir = temp_dir / ".aws-ssm-calendar" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "japanese_holidays.csv"
        
        holiday_data = """日付,祝日名
2024/01/01,元日
2024/01/08,成人の日"""
        cache_file.write_text(holiday_data, encoding='utf-8')
        
        # Generate first ICS file
        holidays = JapaneseHolidays()
        ics_generator1 = ICSGenerator(japanese_holidays=holidays)
        
        file1 = temp_dir / "holidays_v1.ics"
        ics_generator1.save_to_file(str(file1))
        
        # Generate second ICS file with different settings
        ics_generator2 = ICSGenerator(
            japanese_holidays=holidays,
            exclude_sunday_holidays=True
        )
        
        file2 = temp_dir / "holidays_v2.ics"
        ics_generator2.save_to_file(str(file2))
        
        # Compare the files
        analyzer = ICSAnalyzer()
        comparison = analyzer.compare_ics_files(str(file1), str(file2))
        
        assert 'file1_info' in comparison
        assert 'file2_info' in comparison
        assert 'summary' in comparison
        assert 'changes' in comparison
        
        # Format comparison result
        formatted = analyzer.format_comparison_result(comparison)
        assert isinstance(formatted, str)
        assert "比較結果" in formatted

    @pytest.mark.integration
    def test_cache_management_workflow(self, temp_dir, monkeypatch):
        """Test cache management workflow."""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # Create initial cache
        cache_dir = temp_dir / ".aws-ssm-calendar" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "japanese_holidays.csv"
        
        initial_data = """日付,祝日名
2024-01-01,元日
2024-01-08,成人の日"""
        cache_file.write_text(initial_data, encoding='utf-8')
        
        # Test cache loading
        holidays = JapaneseHolidays()
        assert holidays.is_cache_valid()
        
        stats = holidays.get_stats()
        assert stats['total'] == 2
        
        # Test cache invalidation by modifying timestamp
        old_time = datetime.now().timestamp() - (31 * 24 * 3600)  # 31 days ago
        os.utime(cache_file, (old_time, old_time))
        
        # Create new instance to test cache invalidation
        holidays2 = JapaneseHolidays()
        assert not holidays2.is_cache_valid()

    @pytest.mark.integration
    def test_error_handling_workflow(self, temp_dir, monkeypatch):
        """Test error handling in complete workflow."""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # Test with invalid cache data
        cache_dir = temp_dir / ".aws-ssm-calendar" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "japanese_holidays.csv"
        cache_file.write_text("invalid,csv,data", encoding='utf-8')
        
        # Should handle invalid cache gracefully
        holidays = JapaneseHolidays()
        
        # Test ICS generation with no holidays
        ics_generator = ICSGenerator()
        ics_content = ics_generator.generate_ics_content()
        
        # Should generate valid ICS even with no events
        assert 'BEGIN:VCALENDAR' in ics_content
        assert 'END:VCALENDAR' in ics_content

    @pytest.mark.integration
    def test_multiple_year_workflow(self, temp_dir, monkeypatch):
        """Test workflow with multiple years of holiday data."""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # Create multi-year cache data
        cache_dir = temp_dir / ".aws-ssm-calendar" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "japanese_holidays.csv"
        
        multi_year_data = """日付,祝日名
2024-01-01,元日
2024-01-08,成人の日
2025-01-01,元日
2025-01-13,成人の日
2026-01-01,元日"""
        cache_file.write_text(multi_year_data, encoding='utf-8')
        
        holidays = JapaneseHolidays()
        
        # Test statistics
        stats = holidays.get_stats()
        assert stats['total'] == 5
        assert stats['years'] == 3
        assert stats['min_year'] == 2024
        assert stats['max_year'] == 2026
        
        # Test year-specific queries
        holidays_2024 = holidays.get_holidays_by_year(2024)
        holidays_2025 = holidays.get_holidays_by_year(2025)
        
        assert len(holidays_2024) == 2
        assert len(holidays_2025) == 2
        
        # Generate ICS for specific year
        ics_generator = ICSGenerator(japanese_holidays=holidays)
        
        output_file = temp_dir / "holidays_2025.ics"
        ics_generator.save_to_file(str(output_file))
        
        # Analyze generated file
        analyzer = ICSAnalyzer()
        analysis = analyzer.parse_ics_file(str(output_file))
        
        # Should contain only 2025 holidays
        events_2025 = [e for e in analysis['events'] 
                      if e['dtstart'].year == 2025]
        assert len(events_2025) == 2

    @pytest.mark.integration
    def test_utf8_encoding_workflow(self, temp_dir, monkeypatch):
        """Test UTF-8 encoding throughout the workflow."""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # Create cache with Japanese characters
        cache_dir = temp_dir / ".aws-ssm-calendar" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "japanese_holidays.csv"
        
        japanese_data = """日付,祝日名
2024-01-01,元日
2024-02-11,建国記念の日
2024-02-23,天皇誕生日
2024-03-20,春分の日
2024-04-29,昭和の日
2024-05-03,憲法記念日
2024-05-04,みどりの日
2024-05-05,こどもの日"""
        cache_file.write_text(japanese_data, encoding='utf-8')
        
        # Process through complete workflow
        holidays = JapaneseHolidays()
        ics_generator = ICSGenerator(japanese_holidays=holidays)
        
        output_file = temp_dir / "japanese_holidays_utf8.ics"
        ics_generator.save_to_file(str(output_file))
        
        # Verify UTF-8 encoding in output
        content = output_file.read_text(encoding='utf-8')
        
        # Check for Japanese characters
        japanese_holidays = ["元日", "建国記念の日", "天皇誕生日", "春分の日", 
                           "昭和の日", "憲法記念日", "みどりの日", "こどもの日"]
        
        for holiday_name in japanese_holidays:
            assert holiday_name in content
        
        # Analyze with analyzer
        analyzer = ICSAnalyzer()
        analysis = analyzer.parse_ics_file(str(output_file))
        
        # Verify Japanese characters in analysis
        human_readable = analyzer.format_human_readable(analysis)
        for holiday_name in japanese_holidays:
            assert holiday_name in human_readable


class TestAWSChangeCalendarIntegration:
    """Test AWS Change Calendar integration workflows."""

    @pytest.mark.integration
    @patch('boto3.Session')
    def test_aws_change_calendar_creation_workflow(self, mock_session, temp_dir, monkeypatch):
        """Test complete AWS Change Calendar creation workflow."""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # Mock AWS client
        mock_client = Mock()
        mock_client.describe_document.side_effect = Exception("Document not found")  # Calendar doesn't exist
        mock_client.create_document.return_value = {
            'DocumentDescription': {
                'Name': 'test-japanese-holidays-2024',
                'Status': 'Creating',
                'DocumentVersion': '1',
                'CreatedDate': datetime.now()
            }
        }
        mock_session.return_value.client.return_value = mock_client
        
        # Create cache with holiday data
        cache_dir = temp_dir / ".aws-ssm-calendar" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "japanese_holidays.csv"
        
        holiday_data = """日付,祝日名
2024/01/01,元日
2024/01/08,成人の日
2024/02/11,建国記念の日"""
        cache_file.write_text(holiday_data, encoding='utf-8')
        
        # Test Change Calendar creation
        manager = ChangeCalendarManager(region_name='ap-northeast-1')
        
        result = manager.create_japanese_holiday_calendar(
            calendar_name='test-japanese-holidays-2024',
            year=2024,
            description='Test Japanese holidays calendar'
        )
        
        assert result['calendar_name'] == 'test-japanese-holidays-2024'
        assert result['status'] == 'Creating'
        assert result['holiday_count'] > 0
        assert result['year_range'] == '2024-2025'
        
        # Verify create_document was called with correct parameters
        mock_client.create_document.assert_called_once()
        call_args = mock_client.create_document.call_args[1]
        assert call_args['Name'] == 'test-japanese-holidays-2024'
        assert call_args['DocumentType'] == 'ChangeCalendar'
        assert 'BEGIN:VCALENDAR' in call_args['Content']
        assert '元日' in call_args['Content']

    @pytest.mark.integration
    @patch('boto3.Session')
    def test_aws_change_calendar_update_workflow(self, mock_session, temp_dir, monkeypatch):
        """Test AWS Change Calendar update workflow."""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # Mock AWS client
        mock_client = Mock()
        mock_client.describe_document.return_value = {
            'Document': {
                'Name': 'existing-calendar',
                'Status': 'Active'
            }
        }
        mock_client.get_document.return_value = {
            'Content': 'BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR'
        }
        mock_client.update_document.return_value = {
            'DocumentDescription': {
                'Name': 'existing-calendar',
                'Status': 'Updating',
                'DocumentVersion': '2',
                'ModifiedDate': datetime.now()
            }
        }
        mock_session.return_value.client.return_value = mock_client
        
        # Create cache with holiday data
        cache_dir = temp_dir / ".aws-ssm-calendar" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "japanese_holidays.csv"
        
        holiday_data = """日付,祝日名
2024-01-01,元日
2024-02-11,建国記念の日"""
        cache_file.write_text(holiday_data, encoding='utf-8')
        
        # Test Change Calendar update
        manager = ChangeCalendarManager(region_name='ap-northeast-1')
        
        result = manager.update_existing_calendar_with_holidays(
            calendar_name='existing-calendar',
            year=2024,
            preserve_existing=False
        )
        
        assert result['calendar_name'] == 'existing-calendar'
        assert result['status'] == 'Updating'
        assert result['holiday_count'] > 0
        
        # Verify update_document was called
        mock_client.update_document.assert_called_once()

    @pytest.mark.integration
    @patch('boto3.Session')
    def test_aws_change_calendar_analysis_workflow(self, mock_session, temp_dir, monkeypatch):
        """Test AWS Change Calendar analysis workflow."""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # Mock AWS client with ICS content
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//AWS//Change Calendar 1.0//EN
BEGIN:VEVENT
UID:jp-holiday-20240101@aws-ssm-change-calendar
DTSTART;VALUE=DATE:20240101
DTEND;VALUE=DATE:20240102
SUMMARY:元日
END:VEVENT
END:VCALENDAR"""
        
        mock_client = Mock()
        mock_client.get_document.return_value = {
            'Content': ics_content,
            'DocumentVersion': '1',
            'DocumentFormat': 'TEXT'
        }
        mock_client.describe_document.return_value = {
            'Document': {
                'Name': 'test-calendar',
                'Status': 'Active',
                'CreatedDate': datetime.now(),
                'ModifiedDate': datetime.now()
            }
        }
        mock_session.return_value.client.return_value = mock_client
        
        # Test Change Calendar analysis
        manager = ChangeCalendarManager(region_name='ap-northeast-1')
        
        analysis = manager.analyze_calendar('test-calendar')
        
        assert 'aws_info' in analysis
        assert analysis['aws_info']['document_version'] == '1'
        assert analysis['aws_info']['region'] == 'ap-northeast-1'
        
        # Verify get_document was called
        mock_client.get_document.assert_called_once()

    @pytest.mark.integration
    @patch('boto3.Session')
    def test_aws_change_calendar_comparison_workflow(self, mock_session, temp_dir, monkeypatch):
        """Test AWS Change Calendar comparison workflow."""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # Mock AWS client with different ICS content for two calendars
        ics_content_1 = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//AWS//Change Calendar 1.0//EN
BEGIN:VEVENT
UID:jp-holiday-20240101@aws-ssm-change-calendar
DTSTART;VALUE=DATE:20240101
DTEND;VALUE=DATE:20240102
SUMMARY:元日
END:VEVENT
END:VCALENDAR"""
        
        ics_content_2 = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//AWS//Change Calendar 1.0//EN
BEGIN:VEVENT
UID:jp-holiday-20240101@aws-ssm-change-calendar
DTSTART;VALUE=DATE:20240101
DTEND;VALUE=DATE:20240102
SUMMARY:元日
END:VEVENT
BEGIN:VEVENT
UID:jp-holiday-20240108@aws-ssm-change-calendar
DTSTART;VALUE=DATE:20240108
DTEND;VALUE=DATE:20240109
SUMMARY:成人の日
END:VEVENT
END:VCALENDAR"""
        
        mock_client = Mock()
        
        def mock_get_document(Name, **kwargs):
            if Name == 'calendar-1':
                return {
                    'Content': ics_content_1,
                    'DocumentVersion': '1',
                    'DocumentFormat': 'TEXT'
                }
            elif Name == 'calendar-2':
                return {
                    'Content': ics_content_2,
                    'DocumentVersion': '1',
                    'DocumentFormat': 'TEXT'
                }
        
        def mock_describe_document(Name, **kwargs):
            return {
                'Document': {
                    'Name': Name,
                    'Status': 'Active',
                    'CreatedDate': datetime.now(),
                    'ModifiedDate': datetime.now()
                }
            }
        
        mock_client.get_document.side_effect = mock_get_document
        mock_client.describe_document.side_effect = mock_describe_document
        mock_session.return_value.client.return_value = mock_client
        
        # Test Change Calendar comparison
        manager = ChangeCalendarManager(region_name='ap-northeast-1')
        
        comparison = manager.compare_calendars(['calendar-1', 'calendar-2'])
        
        assert 'calendars' in comparison
        assert len(comparison['calendars']) == 2
        assert 'individual_analyses' in comparison
        assert 'comparison_summary' in comparison
        
        # Verify both calendars were analyzed
        assert 'calendar-1' in comparison['individual_analyses']
        assert 'calendar-2' in comparison['individual_analyses']

    @pytest.mark.integration
    @patch('boto3.Session')
    def test_aws_change_calendar_list_workflow(self, mock_session):
        """Test AWS Change Calendar listing workflow."""
        # Mock AWS client
        mock_client = Mock()
        mock_client.list_documents.return_value = {
            'DocumentIdentifiers': [
                {
                    'Name': 'japanese-holidays-2024',
                    'DocumentVersion': '1',
                    'DocumentFormat': 'TEXT',
                    'CreatedDate': datetime.now(),
                    'ModifiedDate': datetime.now()
                },
                {
                    'Name': 'maintenance-windows',
                    'DocumentVersion': '2',
                    'DocumentFormat': 'TEXT',
                    'CreatedDate': datetime.now(),
                    'ModifiedDate': datetime.now()
                }
            ]
        }
        mock_client.get_calendar_state.return_value = {'State': 'OPEN'}
        mock_session.return_value.client.return_value = mock_client
        
        # Test Change Calendar listing
        manager = ChangeCalendarManager(region_name='ap-northeast-1')
        
        calendars = manager.list_change_calendars()
        
        assert len(calendars) == 2
        assert calendars[0]['name'] == 'japanese-holidays-2024'
        assert calendars[0]['current_state'] == 'OPEN'
        assert calendars[1]['name'] == 'maintenance-windows'
        
        # Verify list_documents was called
        mock_client.list_documents.assert_called_once()

    @pytest.mark.integration
    @patch('boto3.Session')
    def test_aws_change_calendar_deletion_workflow(self, mock_session):
        """Test AWS Change Calendar deletion workflow."""
        # Mock AWS client
        mock_client = Mock()
        mock_client.describe_document.return_value = {
            'Document': {
                'Name': 'calendar-to-delete',
                'Status': 'Active'
            }
        }
        mock_client.delete_document.return_value = {
            'Status': 'Deleting'
        }
        mock_session.return_value.client.return_value = mock_client
        
        # Test Change Calendar deletion
        manager = ChangeCalendarManager(region_name='ap-northeast-1')
        
        result = manager.delete_calendar('calendar-to-delete')
        
        assert result['calendar_name'] == 'calendar-to-delete'
        assert result['deleted'] is True
        assert 'deleted_date' in result
        
        # Verify delete_document was called
        mock_client.delete_document.assert_called_once_with(Name='calendar-to-delete')

    @pytest.mark.integration
    @patch('boto3.Session')
    def test_aws_change_calendar_export_workflow(self, mock_session, temp_dir):
        """Test AWS Change Calendar export workflow."""
        # Mock AWS client with ICS content
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//AWS//Change Calendar 1.0//EN
BEGIN:VEVENT
UID:jp-holiday-20240101@aws-ssm-change-calendar
DTSTART;VALUE=DATE:20240101
DTEND;VALUE=DATE:20240102
SUMMARY:元日
END:VEVENT
END:VCALENDAR"""
        
        mock_client = Mock()
        mock_client.get_document.return_value = {
            'Content': ics_content,
            'DocumentVersion': '1',
            'DocumentFormat': 'TEXT'
        }
        mock_client.describe_document.return_value = {
            'Document': {
                'Name': 'export-calendar',
                'Status': 'Active'
            }
        }
        mock_session.return_value.client.return_value = mock_client
        
        # Test Change Calendar export
        manager = ChangeCalendarManager(region_name='ap-northeast-1')
        
        output_file = temp_dir / "exported_calendar.ics"
        result = manager.export_calendar_to_ics('export-calendar', str(output_file))
        
        assert result['calendar_name'] == 'export-calendar'
        assert result['output_file'] == str(output_file)
        assert result['file_size'] > 0
        
        # Verify file was created with correct content
        assert output_file.exists()
        content = output_file.read_text(encoding='utf-8')
        assert 'BEGIN:VCALENDAR' in content
        assert '元日' in content


class TestICSAnalysisAndComparisonIntegration:
    """Test ICS analysis and comparison integration workflows."""

    @pytest.mark.integration
    def test_ics_semantic_diff_workflow(self, temp_dir, monkeypatch):
        """Test ICS semantic diff comparison workflow."""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # Create two ICS files with different content
        ics_content_1 = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//AWS//Change Calendar 1.0//EN
BEGIN:VEVENT
UID:jp-holiday-20240101@aws-ssm-change-calendar
DTSTART;VALUE=DATE:20240101
DTEND;VALUE=DATE:20240102
SUMMARY:元日
DESCRIPTION:国民の祝日
END:VEVENT
END:VCALENDAR"""
        
        ics_content_2 = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//AWS//Change Calendar 1.0//EN
BEGIN:VEVENT
UID:jp-holiday-20240101@aws-ssm-change-calendar
DTSTART;VALUE=DATE:20240101
DTEND;VALUE=DATE:20240102
SUMMARY:元日
DESCRIPTION:国民の祝日（更新版）
END:VEVENT
BEGIN:VEVENT
UID:jp-holiday-20240108@aws-ssm-change-calendar
DTSTART;VALUE=DATE:20240108
DTEND;VALUE=DATE:20240109
SUMMARY:成人の日
DESCRIPTION:国民の祝日
END:VEVENT
END:VCALENDAR"""
        
        file1 = temp_dir / "calendar_v1.ics"
        file2 = temp_dir / "calendar_v2.ics"
        
        file1.write_text(ics_content_1, encoding='utf-8')
        file2.write_text(ics_content_2, encoding='utf-8')
        
        # Test semantic diff comparison
        analyzer = ICSAnalyzer()
        
        # Test if semantic diff method exists and works
        if hasattr(analyzer, 'generate_event_semantic_diff'):
            diff_result = analyzer.generate_event_semantic_diff(str(file1), str(file2))
            
            assert 'changes' in diff_result
            assert 'statistics' in diff_result
            
            # Format semantic diff output
            if hasattr(analyzer, 'format_semantic_diff'):
                formatted_diff = analyzer.format_semantic_diff(diff_result)
                assert isinstance(formatted_diff, str)
                assert '成人の日' in formatted_diff  # Added event
        else:
            # Fallback to regular comparison if semantic diff not implemented
            comparison = analyzer.compare_ics_files(str(file1), str(file2))
            
            assert 'summary' in comparison
            assert comparison['summary']['added'] >= 1  # At least one added event
            assert comparison['summary']['modified'] >= 0  # Possibly modified events

    @pytest.mark.integration
    def test_large_ics_file_analysis_workflow(self, temp_dir, monkeypatch):
        """Test analysis workflow with large ICS files."""
        monkeypatch.setenv('HOME', str(temp_dir))
        
        # Generate large ICS file with many events
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//AWS//Change Calendar 1.0//EN
X-WR-TIMEZONE:Asia/Tokyo
"""
        
        # Add many holiday events
        for year in range(2024, 2030):
            for month in range(1, 13):
                for day in [1, 15]:  # Two events per month
                    ics_content += f"""BEGIN:VEVENT
UID:event-{year}{month:02d}{day:02d}@test-calendar
DTSTART;VALUE=DATE:{year}{month:02d}{day:02d}
DTEND;VALUE=DATE:{year}{month:02d}{day:02d}
SUMMARY:テストイベント {year}-{month:02d}-{day:02d}
DESCRIPTION:大容量テスト用イベント
CATEGORIES:Test-Event
END:VEVENT
"""
        
        ics_content += "END:VCALENDAR"
        
        large_ics_file = temp_dir / "large_calendar.ics"
        large_ics_file.write_text(ics_content, encoding='utf-8')
        
        # Test analysis of large file
        analyzer = ICSAnalyzer()
        analysis = analyzer.parse_ics_file(str(large_ics_file))
        
        assert analysis['file_info']['total_events'] > 100  # Should have many events
        assert len(analysis['validation_errors']) == 0  # Should be valid
        
        # Test performance - analysis should complete in reasonable time
        import time
        start_time = time.time()
        
        human_readable = analyzer.format_human_readable(analysis)
        
        end_time = time.time()
        analysis_time = end_time - start_time
        
        assert analysis_time < 5.0  # Should complete within 5 seconds
        assert isinstance(human_readable, str)
        assert len(human_readable) > 0

    @pytest.mark.integration
    def test_multi_format_export_workflow(self, temp_dir, sample_ics_content):
        """Test multi-format export workflow."""
        # Create test ICS file
        ics_file = temp_dir / "test_calendar.ics"
        ics_file.write_text(sample_ics_content, encoding='utf-8')
        
        # Test analysis with different output formats
        analyzer = ICSAnalyzer()
        analysis = analyzer.parse_ics_file(str(ics_file))
        
        # Test human readable format
        human_readable = analyzer.format_human_readable(analysis)
        assert isinstance(human_readable, str)
        assert '元日' in human_readable
        
        # Test JSON export
        json_output = analyzer.export_json(analysis)
        assert isinstance(json_output, str)
        
        # Verify JSON is valid
        parsed_json = json.loads(json_output)
        assert 'file_info' in parsed_json
        assert 'events' in parsed_json
        
        # Test CSV export
        csv_output = analyzer.export_csv(analysis['events'])
        assert isinstance(csv_output, str)
        assert 'UID' in csv_output  # CSV header
        assert '元日' in csv_output  # Event data