"""AWS SSM Change Calendar management module."""

from typing import Dict, List, Optional
from datetime import datetime, date
import json

from .aws_client import SSMChangeCalendarClient
from .ics_generator import ICSGenerator
from .japanese_holidays import JapaneseHolidays
from .calendar_analyzer import ICSAnalyzer


class ChangeCalendarManager:
    """Manage AWS SSM Change Calendars with Japanese holidays."""
    
    def __init__(self, region_name: str = 'ap-northeast-1', profile_name: Optional[str] = None):
        """Initialize Change Calendar Manager.
        
        Args:
            region_name: AWS region
            profile_name: AWS profile name (optional)
        """
        self.ssm_client = SSMChangeCalendarClient(region_name, profile_name)
        self.ics_generator = ICSGenerator()
        self.japanese_holidays = JapaneseHolidays()
        self.analyzer = ICSAnalyzer()
        self.region_name = region_name
    
    def create_japanese_holiday_calendar(self, 
                                       calendar_name: str,
                                       year: int,
                                       description: str = "") -> Dict:
        """Create a new Change Calendar with Japanese holidays.
        
        Args:
            calendar_name: Name for the new calendar
            year: Year for holidays (will include current year and next year)
            description: Optional description for the calendar
            
        Returns:
            Creation result with calendar information
            
        Raises:
            Exception: If calendar creation fails
        """
        try:
            # Check if calendar already exists
            if self.ssm_client.calendar_exists(calendar_name):
                raise ValueError(f"Change Calendar '{calendar_name}' already exists")
            
            # Generate ICS content with Japanese holidays
            start_date = date(year, 1, 1)
            end_date = date(year + 1, 12, 31)  # Include next year
            
            self.ics_generator.clear_events()
            self.ics_generator.add_japanese_holidays(start_date, end_date)
            
            ics_content = self.ics_generator.generate_ics_content()
            
            # Prepare tags
            tags = [
                {'Key': 'Source', 'Value': 'JapaneseGovernment'},
                {'Key': 'Type', 'Value': 'Holiday'},
                {'Key': 'Year', 'Value': str(year)},
                {'Key': 'CreatedBy', 'Value': 'AWS-SSM-Calendar-Tool'},
                {'Key': 'CreatedDate', 'Value': datetime.now().isoformat()}
            ]
            
            if description:
                tags.append({'Key': 'Description', 'Value': description})
            
            # Create the Change Calendar
            response = self.ssm_client.create_change_calendar(
                calendar_name=calendar_name,
                ics_content=ics_content,
                tags=tags
            )
            
            # Get holiday statistics
            holidays = self.japanese_holidays.get_holidays_in_range(start_date, end_date)
            
            return {
                'calendar_name': calendar_name,
                'status': response['DocumentDescription']['Status'],
                'version': response['DocumentDescription']['DocumentVersion'],
                'holiday_count': len(holidays),
                'year_range': f"{year}-{year + 1}",
                'ics_size': len(ics_content),
                'created_date': response['DocumentDescription']['CreatedDate']
            }
            
        except Exception as e:
            raise Exception(f"Failed to create Japanese holiday calendar: {e}")
    
    def update_existing_calendar_with_holidays(self, 
                                             calendar_name: str,
                                             year: int,
                                             preserve_existing: bool = True) -> Dict:
        """Update an existing Change Calendar to include Japanese holidays.
        
        Args:
            calendar_name: Name of the existing calendar
            year: Year for holidays
            preserve_existing: Whether to preserve existing events
            
        Returns:
            Update result with calendar information
            
        Raises:
            Exception: If calendar update fails
        """
        try:
            # Check if calendar exists
            if not self.ssm_client.calendar_exists(calendar_name):
                raise ValueError(f"Change Calendar '{calendar_name}' does not exist")
            
            if preserve_existing:
                # Get existing calendar content
                existing_calendar = self.ssm_client.get_change_calendar(calendar_name)
                existing_content = existing_calendar.get('Content', '')
                
                # TODO: Parse existing ICS content and merge with holidays
                # For now, we'll create a new calendar with holidays only
                print("Warning: Preserving existing events is not yet implemented")
                print("Creating new calendar with holidays only")
            
            # Generate new ICS content with Japanese holidays
            start_date = date(year, 1, 1)
            end_date = date(year + 1, 12, 31)
            
            self.ics_generator.clear_events()
            self.ics_generator.add_japanese_holidays(start_date, end_date)
            
            ics_content = self.ics_generator.generate_ics_content()
            
            # Update the Change Calendar
            response = self.ssm_client.update_change_calendar(
                calendar_name=calendar_name,
                ics_content=ics_content
            )
            
            # Get holiday statistics
            holidays = self.japanese_holidays.get_holidays_in_range(start_date, end_date)
            
            return {
                'calendar_name': calendar_name,
                'status': response['DocumentDescription']['Status'],
                'version': response['DocumentDescription']['DocumentVersion'],
                'holiday_count': len(holidays),
                'year_range': f"{year}-{year + 1}",
                'ics_size': len(ics_content),
                'updated_date': response['DocumentDescription']['ModifiedDate']
            }
            
        except Exception as e:
            raise Exception(f"Failed to update calendar with holidays: {e}")
    
    def get_calendar_info(self, calendar_name: str) -> Dict:
        """Get information about a Change Calendar.
        
        Args:
            calendar_name: Name of the calendar
            
        Returns:
            Calendar information
        """
        try:
            # Get calendar document info
            calendar_doc = self.ssm_client.get_change_calendar(calendar_name)
            
            # Get calendar state
            state = self.ssm_client.get_calendar_state(calendar_name)
            
            return {
                'name': calendar_name,
                'status': calendar_doc.get('Status', 'Unknown'),
                'version': calendar_doc.get('DocumentVersion', 'Unknown'),
                'format': calendar_doc.get('DocumentFormat', 'Unknown'),
                'current_state': state,
                'content_size': len(calendar_doc.get('Content', '')),
                'created_date': calendar_doc.get('CreatedDate'),
                'modified_date': calendar_doc.get('ModifiedDate')
            }
            
        except Exception as e:
            raise Exception(f"Failed to get calendar info: {e}")
    
    def list_change_calendars(self) -> List[Dict]:
        """List all Change Calendars in the account.
        
        Returns:
            List of calendar information
        """
        try:
            calendars = self.ssm_client.list_change_calendars()
            
            calendar_list = []
            for calendar in calendars:
                try:
                    # Get additional info for each calendar
                    state = self.ssm_client.get_calendar_state(calendar['Name'])
                    
                    calendar_info = {
                        'name': calendar['Name'],
                        'version': calendar.get('DocumentVersion', 'Unknown'),
                        'format': calendar.get('DocumentFormat', 'Unknown'),
                        'current_state': state,
                        'created_date': calendar.get('CreatedDate'),
                        'modified_date': calendar.get('ModifiedDate')
                    }
                    
                    calendar_list.append(calendar_info)
                    
                except Exception as e:
                    # If we can't get state, still include basic info
                    calendar_info = {
                        'name': calendar['Name'],
                        'version': calendar.get('DocumentVersion', 'Unknown'),
                        'format': calendar.get('DocumentFormat', 'Unknown'),
                        'current_state': 'Unknown',
                        'error': str(e)
                    }
                    calendar_list.append(calendar_info)
            
            return calendar_list
            
        except Exception as e:
            raise Exception(f"Failed to list Change Calendars: {e}")
    
    def delete_calendar(self, calendar_name: str) -> Dict:
        """Delete a Change Calendar.
        
        Args:
            calendar_name: Name of the calendar to delete
            
        Returns:
            Deletion result
        """
        try:
            # Check if calendar exists
            if not self.ssm_client.calendar_exists(calendar_name):
                raise ValueError(f"Change Calendar '{calendar_name}' does not exist")
            
            # Delete the calendar
            response = self.ssm_client.delete_change_calendar(calendar_name)
            
            return {
                'calendar_name': calendar_name,
                'deleted': True,
                'deleted_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Failed to delete calendar: {e}")
    
    def export_calendar_to_ics(self, calendar_name: str, output_file: str) -> Dict:
        """Export a Change Calendar to ICS file.
        
        Args:
            calendar_name: Name of the calendar to export
            output_file: Output file path
            
        Returns:
            Export result
        """
        try:
            # Get calendar content
            calendar_doc = self.ssm_client.get_change_calendar(calendar_name)
            ics_content = calendar_doc.get('Content', '')
            
            # Save to file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(ics_content)
            
            return {
                'calendar_name': calendar_name,
                'output_file': output_file,
                'file_size': len(ics_content),
                'exported_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Failed to export calendar: {e}")
    
    def analyze_calendar(self, calendar_name: str) -> Dict:
        """Analyze a Change Calendar and provide insights.
        
        Args:
            calendar_name: Name of the calendar to analyze
            
        Returns:
            Analysis results
        """
        try:
            # Get calendar content
            calendar_doc = self.ssm_client.get_change_calendar(calendar_name)
            ics_content = calendar_doc.get('Content', '')
            
            if not ics_content:
                raise ValueError(f"Calendar '{calendar_name}' has no content")
            
            # Perform analysis
            analysis = self.analyzer.analyze_calendar(calendar_name, ics_content)
            
            # Add AWS-specific information
            analysis['aws_info'] = {
                'region': self.region_name,
                'document_version': calendar_doc.get('DocumentVersion', 'Unknown'),
                'document_format': calendar_doc.get('DocumentFormat', 'Unknown'),
                'created_date': calendar_doc.get('CreatedDate'),
                'modified_date': calendar_doc.get('ModifiedDate'),
                'content_size': len(ics_content)
            }
            
            return analysis
            
        except Exception as e:
            raise Exception(f"Failed to analyze calendar: {e}")
    
    def compare_calendars(self, calendar_names: List[str]) -> Dict:
        """Compare multiple Change Calendars.
        
        Args:
            calendar_names: List of calendar names to compare
            
        Returns:
            Comparison results
        """
        try:
            if len(calendar_names) < 2:
                raise ValueError("At least 2 calendars are required for comparison")
            
            analyses = {}
            for calendar_name in calendar_names:
                analyses[calendar_name] = self.analyze_calendar(calendar_name)
            
            # Generate comparison summary
            comparison = {
                'calendars': list(calendar_names),
                'comparison_date': datetime.now().isoformat(),
                'individual_analyses': analyses,
                'comparison_summary': self._generate_comparison_summary(analyses)
            }
            
            return comparison
            
        except Exception as e:
            raise Exception(f"Failed to compare calendars: {e}")
    
    def _generate_comparison_summary(self, analyses: Dict) -> Dict:
        """Generate comparison summary from multiple analyses.
        
        Args:
            analyses: Dictionary of calendar analyses
            
        Returns:
            Comparison summary
        """
        summary = {
            'event_counts': {},
            'coverage_comparison': {},
            'holiday_coverage': {},
            'recommendations': []
        }
        
        for calendar_name, analysis in analyses.items():
            basic_stats = analysis.get('basic_stats', {})
            event_analysis = analysis.get('event_analysis', {})
            coverage = analysis.get('coverage_analysis', {})
            
            summary['event_counts'][calendar_name] = basic_stats.get('total_events', 0)
            summary['coverage_comparison'][calendar_name] = coverage.get('coverage_percentage', 0)
            summary['holiday_coverage'][calendar_name] = event_analysis.get('japanese_holidays_count', 0)
        
        # Generate comparison recommendations
        event_counts = list(summary['event_counts'].values())
        if event_counts:
            max_events = max(event_counts)
            min_events = min(event_counts)
            
            if max_events - min_events > 10:
                summary['recommendations'].append(
                    f"イベント数に大きな差があります（最大: {max_events}, 最小: {min_events}）。"
                    "カレンダー間の一貫性を確保することを検討してください。"
                )
        
        holiday_counts = list(summary['holiday_coverage'].values())
        if holiday_counts and max(holiday_counts) > 0 and min(holiday_counts) == 0:
            summary['recommendations'].append(
                "一部のカレンダーに祝日が設定されていません。全カレンダーに祝日を追加することを推奨します。"
            )
        
        return summary