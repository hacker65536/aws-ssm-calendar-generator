"""
Unit tests for JapaneseHolidays class.
Tests requirement 1: 日本祝日データ取得・管理
"""

import pytest
from unittest.mock import Mock, patch, mock_open
from datetime import date, datetime
import tempfile
import os

from src.japanese_holidays import JapaneseHolidays, HolidayDataError


class TestJapaneseHolidays:
    """Test cases for JapaneseHolidays class."""

    def test_init_creates_cache_directory(self, temp_dir, monkeypatch):
        """Test that initialization creates cache directory."""
        monkeypatch.setenv("HOME", str(temp_dir))
        
        holidays = JapaneseHolidays()
        
        expected_cache_dir = temp_dir / ".aws-ssm-calendar" / "cache"
        expected_cache_file = expected_cache_dir / "japanese_holidays.csv"
        assert expected_cache_dir.exists()
        assert holidays.cache_file == str(expected_cache_file)

    def test_is_cache_valid_with_fresh_cache(self, temp_dir, monkeypatch):
        """Test cache validity check with fresh cache."""
        monkeypatch.setenv("HOME", str(temp_dir))
        
        # Create fresh cache file
        cache_dir = temp_dir / ".aws-ssm-calendar" / "cache"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "japanese_holidays.csv"
        cache_file.write_text("test data")
        
        holidays = JapaneseHolidays()
        assert holidays.is_cache_valid() is True

    def test_is_cache_valid_with_old_cache(self, temp_dir, monkeypatch):
        """Test cache validity check with old cache."""
        monkeypatch.setenv("HOME", str(temp_dir))
        
        # Create old cache file
        cache_dir = temp_dir / ".aws-ssm-calendar" / "cache"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "japanese_holidays.csv"
        cache_file.write_text("test data")
        
        # Mock file modification time to be old
        old_time = datetime.now().timestamp() - (31 * 24 * 3600)  # 31 days ago
        os.utime(cache_file, (old_time, old_time))
        
        holidays = JapaneseHolidays()
        assert holidays.is_cache_valid() is False

    @patch('requests.get')
    def test_fetch_official_data_success(self, mock_get, temp_dir, monkeypatch):
        """Test successful fetching of official holiday data."""
        monkeypatch.setenv("HOME", str(temp_dir))
        
        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.content = "日付,祝日名\n2024-01-01,元日".encode('shift_jis')
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        holidays = JapaneseHolidays()
        data = holidays.fetch_official_data()
        
        assert "元日" in data
        mock_get.assert_called_once()

    @patch('requests.get')
    def test_fetch_official_data_network_error(self, mock_get, temp_dir, monkeypatch):
        """Test network error handling during data fetch."""
        monkeypatch.setenv("HOME", str(temp_dir))
        
        # Mock network error
        mock_get.side_effect = Exception("Network error")
        
        holidays = JapaneseHolidays()
        
        with pytest.raises(HolidayDataError):
            holidays.fetch_official_data()

    def test_detect_encoding_shift_jis(self, temp_dir, monkeypatch):
        """Test encoding detection for Shift_JIS data."""
        monkeypatch.setenv("HOME", str(temp_dir))
        
        holidays = JapaneseHolidays()
        
        # Test Shift_JIS encoded data
        shift_jis_data = "日付,祝日名\n2024-01-01,元日".encode('shift_jis')
        encoding = holidays.detect_encoding(shift_jis_data)
        
        assert encoding in ['shift_jis', 'cp932']

    def test_convert_to_utf8(self, temp_dir, monkeypatch):
        """Test conversion to UTF-8."""
        monkeypatch.setenv("HOME", str(temp_dir))
        
        holidays = JapaneseHolidays()
        
        # Test conversion from Shift_JIS to UTF-8
        original_data = "日付,祝日名\n2024-01-01,元日"
        shift_jis_data = original_data.encode('shift_jis').decode('shift_jis')
        
        utf8_data = holidays.convert_to_utf8(shift_jis_data, 'shift_jis')
        
        assert "元日" in utf8_data
        assert isinstance(utf8_data, str)

    def test_filter_current_year_onwards(self, temp_dir, monkeypatch):
        """Test filtering holidays from current year onwards."""
        monkeypatch.setenv("HOME", str(temp_dir))
        
        holidays = JapaneseHolidays()
        
        # Create test holiday data with past and future dates
        test_holidays = [
            (date(2020, 1, 1), "元日"),
            (date(2024, 1, 1), "元日"),
            (date(2025, 1, 1), "元日"),
        ]
        
        current_year = datetime.now().year
        filtered = holidays.filter_current_year_onwards(test_holidays)
        
        # Should only include current year and future
        for holiday_date, _ in filtered:
            assert holiday_date.year >= current_year

    def test_is_holiday_true(self, temp_dir, monkeypatch):
        """Test holiday check for actual holiday."""
        monkeypatch.setenv("HOME", str(temp_dir))
        
        # Mock cache with test data
        cache_dir = temp_dir / ".aws-ssm-calendar" / "cache"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "japanese_holidays.csv"
        cache_file.write_text("日付,祝日名\n2024-01-01,元日", encoding='utf-8')
        
        holidays = JapaneseHolidays()
        
        assert holidays.is_holiday(date(2024, 1, 1)) is True

    def test_is_holiday_false(self, temp_dir, monkeypatch):
        """Test holiday check for non-holiday."""
        monkeypatch.setenv("HOME", str(temp_dir))
        
        # Mock cache with test data
        cache_dir = temp_dir / ".aws-ssm-calendar" / "cache"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "japanese_holidays.csv"
        cache_file.write_text("日付,祝日名\n2024-01-01,元日", encoding='utf-8')
        
        holidays = JapaneseHolidays()
        
        assert holidays.is_holiday(date(2024, 12, 25)) is False

    def test_get_holiday_name(self, temp_dir, monkeypatch):
        """Test getting holiday name."""
        monkeypatch.setenv("HOME", str(temp_dir))
        
        # Mock cache with test data
        cache_dir = temp_dir / ".aws-ssm-calendar" / "cache"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "japanese_holidays.csv"
        cache_file.write_text("日付,祝日名\n2024-01-01,元日", encoding='utf-8')
        
        holidays = JapaneseHolidays()
        
        assert holidays.get_holiday_name(date(2024, 1, 1)) == "元日"
        assert holidays.get_holiday_name(date(2024, 12, 25)) is None

    def test_get_stats(self, temp_dir, monkeypatch):
        """Test getting holiday statistics."""
        monkeypatch.setenv("HOME", str(temp_dir))
        
        # Mock cache with test data
        cache_dir = temp_dir / ".aws-ssm-calendar" / "cache"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "japanese_holidays.csv"
        cache_file.write_text(
            "日付,祝日名\n2024-01-01,元日\n2024-01-08,成人の日\n2025-01-01,元日", 
            encoding='utf-8'
        )
        
        holidays = JapaneseHolidays()
        stats = holidays.get_stats()
        
        assert stats['total'] == 3
        assert stats['years'] == 2
        assert stats['min_year'] == 2024
        assert stats['max_year'] == 2025

    def test_get_holidays_by_year(self, temp_dir, monkeypatch):
        """Test getting holidays by specific year."""
        monkeypatch.setenv("HOME", str(temp_dir))
        
        # Mock cache with test data
        cache_dir = temp_dir / ".aws-ssm-calendar" / "cache"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "japanese_holidays.csv"
        cache_file.write_text(
            "日付,祝日名\n2024-01-01,元日\n2024-01-08,成人の日\n2025-01-01,元日", 
            encoding='utf-8'
        )
        
        holidays = JapaneseHolidays()
        holidays_2024 = holidays.get_holidays_by_year(2024)
        
        assert len(holidays_2024) == 2
        assert all(h[0].year == 2024 for h in holidays_2024)

    def test_get_next_holiday(self, temp_dir, monkeypatch):
        """Test getting next holiday from a given date."""
        monkeypatch.setenv("HOME", str(temp_dir))
        
        # Mock cache with test data
        cache_dir = temp_dir / ".aws-ssm-calendar" / "cache"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "japanese_holidays.csv"
        cache_file.write_text(
            "日付,祝日名\n2024-01-01,元日\n2024-01-08,成人の日", 
            encoding='utf-8'
        )
        
        holidays = JapaneseHolidays()
        next_holiday = holidays.get_next_holiday(date(2024, 1, 2))
        
        assert next_holiday is not None
        assert next_holiday[0] == date(2024, 1, 8)
        assert next_holiday[1] == "成人の日"