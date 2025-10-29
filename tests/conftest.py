"""
Pytest configuration and shared fixtures for the test suite.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import date, datetime
from unittest.mock import Mock, patch
import json
import os

# Test data constants
TEST_HOLIDAYS_CSV = """日付,祝日名
2024-01-01,元日
2024-01-08,成人の日
2024-02-11,建国記念の日
2024-02-23,天皇誕生日
2024-03-20,春分の日
2024-04-29,昭和の日
2024-05-03,憲法記念日
2024-05-04,みどりの日
2024-05-05,こどもの日
2024-07-15,海の日
2024-08-11,山の日
2024-09-16,敬老の日
2024-09-22,秋分の日
2024-10-14,スポーツの日
2024-11-03,文化の日
2024-11-23,勤労感謝の日"""

TEST_AWS_CHANGE_CALENDAR = {
    "schemaVersion": "1.0",
    "name": "test-calendar",
    "description": "Test Change Calendar",
    "calendarType": "DEFAULT_OPEN",
    "events": [
        {
            "name": "Test Event 1",
            "startTime": "2024-01-01T00:00:00Z",
            "endTime": "2024-01-02T00:00:00Z",
            "description": "Test event description"
        }
    ]
}

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)

@pytest.fixture
def mock_cache_dir(temp_dir):
    """Mock cache directory for testing."""
    cache_dir = temp_dir / "cache"
    cache_dir.mkdir()
    return cache_dir

@pytest.fixture
def test_holidays_csv(temp_dir):
    """Create a test holidays CSV file."""
    csv_file = temp_dir / "test_holidays.csv"
    csv_file.write_text(TEST_HOLIDAYS_CSV, encoding='utf-8')
    return csv_file

@pytest.fixture
def mock_japanese_holidays():
    """Mock JapaneseHolidays instance with test data."""
    from src.japanese_holidays import JapaneseHolidays
    
    holidays = Mock(spec=JapaneseHolidays)
    holidays.get_stats.return_value = {
        'total': 16,
        'years': 1,
        'min_year': 2024,
        'max_year': 2024
    }
    holidays.get_holidays_by_year.return_value = [
        (date(2024, 1, 1), "元日"),
        (date(2024, 1, 8), "成人の日"),
        (date(2024, 2, 11), "建国記念の日"),
    ]
    holidays.is_holiday.return_value = True
    holidays.get_holiday_name.return_value = "元日"
    return holidays

@pytest.fixture
def mock_aws_client():
    """Mock AWS SSM client for testing."""
    client = Mock()
    client.get_document.return_value = {
        'Content': json.dumps(TEST_AWS_CHANGE_CALENDAR)
    }
    client.list_documents.return_value = {
        'DocumentIdentifiers': [
            {
                'Name': 'test-calendar',
                'DocumentType': 'ChangeCalendar'
            }
        ]
    }
    client.get_calendar_state.return_value = {
        'State': 'OPEN',
        'AtTime': '2024-01-01T00:00:00Z'
    }
    return client

@pytest.fixture
def sample_ics_content():
    """Sample ICS content for testing."""
    return """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//AWS//Change Calendar 1.0//EN
X-CALENDAR-TYPE:DEFAULT_OPEN
X-WR-CALDESC:
X-CALENDAR-CMEVENTS:DISABLED
X-WR-TIMEZONE:Asia/Tokyo

BEGIN:VTIMEZONE
TZID:Asia/Tokyo
BEGIN:STANDARD
DTSTART:19700101T000000
TZOFFSETTFROM:+0900
TZOFFSETTO:+0900
TZNAME:JST
END:STANDARD
END:VTIMEZONE

BEGIN:VEVENT
UID:jp-holiday-20240101@aws-ssm-change-calendar
DTSTAMP:20241029T120000Z
DTSTART;TZID=Asia/Tokyo:20240101T000000
DTEND;TZID=Asia/Tokyo:20240102T000000
SUMMARY:日本の祝日: 元日
DESCRIPTION:日本の国民の祝日: 元日
CATEGORIES:Japanese-Holiday
END:VEVENT

END:VCALENDAR"""

@pytest.fixture
def mock_network_requests():
    """Mock network requests for testing."""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.content = TEST_HOLIDAYS_CSV.encode('shift_jis')
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        yield mock_get

@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch, temp_dir):
    """Setup test environment with temporary directories."""
    # Set up temporary cache directory
    cache_dir = temp_dir / ".aws-ssm-calendar" / "cache"
    cache_dir.mkdir(parents=True)
    
    # Mock home directory to use temp directory
    monkeypatch.setenv("HOME", str(temp_dir))
    
    # Ensure clean environment
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)
    
    return temp_dir