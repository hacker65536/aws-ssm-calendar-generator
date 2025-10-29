"""
Unit tests for ICSGenerator class.
Tests requirement 2: AWS SSM Change Calendar用ICS変換
"""

import pytest
from unittest.mock import Mock, patch
from datetime import date, datetime
import tempfile

from src.ics_generator import ICSGenerator, ICSGenerationError


class TestICSGenerator:
    """Test cases for ICSGenerator class."""

    def test_init_with_japanese_holidays(self, mock_japanese_holidays):
        """Test initialization with JapaneseHolidays instance."""
        generator = ICSGenerator(japanese_holidays=mock_japanese_holidays)
        
        assert generator.japanese_holidays == mock_japanese_holidays
        assert generator.calendar is not None

    def test_init_without_japanese_holidays(self):
        """Test initialization without JapaneseHolidays instance."""
        generator = ICSGenerator()
        
        assert generator.japanese_holidays is None
        assert generator.calendar is not None

    def test_create_aws_ssm_calendar(self):
        """Test AWS SSM calendar creation with proper headers."""
        generator = ICSGenerator()
        calendar = generator.create_aws_ssm_calendar()
        
        # Check required AWS SSM properties
        assert calendar['prodid'] == '-//AWS//Change Calendar 1.0//EN'
        assert calendar['version'] == '2.0'
        assert 'x-calendar-type' in calendar
        assert 'x-wr-timezone' in calendar

    def test_add_timezone_definition(self):
        """Test adding Asia/Tokyo timezone definition."""
        generator = ICSGenerator()
        generator.add_timezone_definition()
        
        # Check if timezone component was added
        timezone_found = False
        for component in generator.calendar.walk():
            if component.name == "VTIMEZONE":
                timezone_found = True
                assert component['tzid'] == 'Asia/Tokyo'
                break
        
        assert timezone_found

    def test_generate_holiday_event(self):
        """Test generating individual holiday event."""
        generator = ICSGenerator()
        
        holiday_date = date(2024, 1, 1)
        holiday_name = "元日"
        
        event = generator.generate_holiday_event(holiday_date, holiday_name)
        
        assert event['summary'] == f"日本の祝日: {holiday_name}"
        assert event['categories'] == "Japanese-Holiday"
        assert 'uid' in event
        assert 'dtstamp' in event

    def test_convert_holidays_to_events(self, mock_japanese_holidays):
        """Test converting holidays to ICS events."""
        generator = ICSGenerator(japanese_holidays=mock_japanese_holidays)
        
        holidays = [
            (date(2024, 1, 1), "元日"),
            (date(2024, 1, 8), "成人の日"),
        ]
        
        events = generator.convert_holidays_to_events(holidays)
        
        assert len(events) == 2
        assert all('uid' in event for event in events)
        assert all('summary' in event for event in events)

    def test_add_japanese_holidays_for_year(self, mock_japanese_holidays):
        """Test adding Japanese holidays for specific year."""
        generator = ICSGenerator(japanese_holidays=mock_japanese_holidays)
        
        generator.add_japanese_holidays_for_year(2024)
        
        # Verify holidays were added to calendar
        events = list(generator.calendar.walk('vevent'))
        assert len(events) > 0

    def test_generate_ics_content(self, mock_japanese_holidays):
        """Test generating ICS content string."""
        generator = ICSGenerator(japanese_holidays=mock_japanese_holidays)
        generator.add_japanese_holidays_for_year(2024)
        
        ics_content = generator.generate_ics_content()
        
        assert isinstance(ics_content, str)
        assert 'BEGIN:VCALENDAR' in ics_content
        assert 'END:VCALENDAR' in ics_content
        assert '-//AWS//Change Calendar 1.0//EN' in ics_content
        assert 'Asia/Tokyo' in ics_content

    def test_save_to_file(self, mock_japanese_holidays, temp_dir):
        """Test saving ICS content to file."""
        generator = ICSGenerator(japanese_holidays=mock_japanese_holidays)
        generator.add_japanese_holidays_for_year(2024)
        
        output_file = temp_dir / "test_output.ics"
        generator.save_to_file(str(output_file))
        
        assert output_file.exists()
        
        # Verify file content
        content = output_file.read_text(encoding='utf-8')
        assert 'BEGIN:VCALENDAR' in content
        assert '日本の祝日' in content  # UTF-8 encoding test

    def test_validate_aws_ssm_compatibility(self, mock_japanese_holidays):
        """Test AWS SSM compatibility validation."""
        generator = ICSGenerator(japanese_holidays=mock_japanese_holidays)
        
        is_compatible = generator.validate_aws_ssm_compatibility()
        
        assert is_compatible is True

    def test_get_generation_stats(self, mock_japanese_holidays):
        """Test getting generation statistics."""
        generator = ICSGenerator(japanese_holidays=mock_japanese_holidays)
        generator.add_japanese_holidays_for_year(2024)
        
        stats = generator.get_generation_stats()
        
        assert 'total_events' in stats
        assert 'holiday_events' in stats
        assert 'has_timezone' in stats
        assert 'aws_ssm_compatible' in stats
        assert stats['has_timezone'] is True
        assert stats['aws_ssm_compatible'] is True

    def test_filter_sunday_holidays_enabled(self, mock_japanese_holidays):
        """Test filtering Sunday holidays when enabled."""
        # Mock Sunday holiday
        mock_japanese_holidays.get_holidays_by_year.return_value = [
            (date(2024, 2, 11), "建国記念の日"),  # Sunday in 2024
            (date(2024, 1, 1), "元日"),  # Monday in 2024
        ]
        
        generator = ICSGenerator(
            japanese_holidays=mock_japanese_holidays,
            exclude_sunday_holidays=True
        )
        generator.add_japanese_holidays_for_year(2024)
        
        events = list(generator.calendar.walk('vevent'))
        
        # Should exclude Sunday holiday
        summaries = [event['summary'] for event in events]
        assert any("元日" in summary for summary in summaries)
        # Note: This test assumes the mock data structure

    def test_filter_sunday_holidays_disabled(self, mock_japanese_holidays):
        """Test including Sunday holidays when filtering disabled."""
        # Mock Sunday holiday
        mock_japanese_holidays.get_holidays_by_year.return_value = [
            (date(2024, 2, 11), "建国記念の日"),  # Sunday in 2024
            (date(2024, 1, 1), "元日"),  # Monday in 2024
        ]
        
        generator = ICSGenerator(
            japanese_holidays=mock_japanese_holidays,
            exclude_sunday_holidays=False
        )
        generator.add_japanese_holidays_for_year(2024)
        
        events = list(generator.calendar.walk('vevent'))
        
        # Should include all holidays
        assert len(events) >= 2

    def test_error_handling_invalid_holiday_data(self):
        """Test error handling for invalid holiday data."""
        generator = ICSGenerator()
        
        # Test with invalid holiday data
        invalid_holidays = [
            ("invalid_date", "Invalid Holiday"),
        ]
        
        with pytest.raises(ICSGenerationError):
            generator.convert_holidays_to_events(invalid_holidays)

    def test_utf8_encoding_in_content(self, mock_japanese_holidays):
        """Test UTF-8 encoding in generated content."""
        generator = ICSGenerator(japanese_holidays=mock_japanese_holidays)
        generator.add_japanese_holidays_for_year(2024)
        
        ics_content = generator.generate_ics_content()
        
        # Verify Japanese characters are properly encoded
        assert "日本の祝日" in ics_content
        assert "元日" in ics_content

    def test_unique_uid_generation(self, mock_japanese_holidays):
        """Test that UIDs are unique for different holidays."""
        generator = ICSGenerator(japanese_holidays=mock_japanese_holidays)
        
        holidays = [
            (date(2024, 1, 1), "元日"),
            (date(2024, 1, 8), "成人の日"),
        ]
        
        events = generator.convert_holidays_to_events(holidays)
        
        uids = [event['uid'] for event in events]
        assert len(uids) == len(set(uids))  # All UIDs should be unique