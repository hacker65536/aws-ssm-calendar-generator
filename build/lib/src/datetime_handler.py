"""Date and time handling utilities."""

from datetime import datetime, timezone
from dateutil import parser, tz
import pytz
from typing import Optional, Union


class DateTimeHandler:
    """Handle date/time operations and timezone conversions."""
    
    def __init__(self, default_timezone: str = 'UTC'):
        """Initialize datetime handler.
        
        Args:
            default_timezone: Default timezone for operations
        """
        self.default_tz = pytz.timezone(default_timezone)
    
    def parse_datetime(self, dt_string: str, timezone_name: Optional[str] = None) -> datetime:
        """Parse datetime string with timezone handling.
        
        Args:
            dt_string: Datetime string to parse
            timezone_name: Timezone name (optional)
            
        Returns:
            Parsed datetime object with timezone
        """
        try:
            # Parse the datetime string
            dt = parser.parse(dt_string)
            
            # If no timezone info, assume default timezone
            if dt.tzinfo is None:
                target_tz = pytz.timezone(timezone_name) if timezone_name else self.default_tz
                dt = target_tz.localize(dt)
            
            return dt
        except (ValueError, parser.ParserError) as e:
            raise ValueError(f"Failed to parse datetime '{dt_string}': {e}")
    
    def convert_timezone(self, dt: datetime, target_timezone: str) -> datetime:
        """Convert datetime to target timezone.
        
        Args:
            dt: Source datetime
            target_timezone: Target timezone name
            
        Returns:
            Converted datetime
        """
        target_tz = pytz.timezone(target_timezone)
        
        # If datetime is naive, assume it's in default timezone
        if dt.tzinfo is None:
            dt = self.default_tz.localize(dt)
        
        return dt.astimezone(target_tz)
    
    def to_utc(self, dt: datetime) -> datetime:
        """Convert datetime to UTC.
        
        Args:
            dt: Source datetime
            
        Returns:
            UTC datetime
        """
        return self.convert_timezone(dt, 'UTC')
    
    def format_for_ics(self, dt: datetime) -> str:
        """Format datetime for ICS file.
        
        Args:
            dt: Datetime to format
            
        Returns:
            ICS-formatted datetime string
        """
        # Convert to UTC for ICS format
        utc_dt = self.to_utc(dt)
        return utc_dt.strftime('%Y%m%dT%H%M%SZ')
    
    def parse_aws_datetime(self, aws_dt_string: str) -> datetime:
        """Parse AWS datetime format.
        
        Args:
            aws_dt_string: AWS datetime string
            
        Returns:
            Parsed datetime
        """
        # AWS typically uses ISO 8601 format
        try:
            return datetime.fromisoformat(aws_dt_string.replace('Z', '+00:00'))
        except ValueError:
            # Fallback to general parsing
            return self.parse_datetime(aws_dt_string)
    
    def get_current_utc(self) -> datetime:
        """Get current UTC datetime.
        
        Returns:
            Current UTC datetime
        """
        return datetime.now(timezone.utc)
    
    def is_valid_timezone(self, timezone_name: str) -> bool:
        """Check if timezone name is valid.
        
        Args:
            timezone_name: Timezone name to validate
            
        Returns:
            True if valid timezone
        """
        try:
            pytz.timezone(timezone_name)
            return True
        except pytz.UnknownTimeZoneError:
            return False