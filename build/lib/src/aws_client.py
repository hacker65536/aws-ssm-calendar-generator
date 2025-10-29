"""AWS SSM Change Calendar client module."""

import boto3
from typing import Dict, List, Optional
from botocore.exceptions import ClientError


class SSMChangeCalendarClient:
    """AWS SSM Change Calendar operations."""
    
    def __init__(self, region_name: str = 'us-east-1', profile_name: Optional[str] = None):
        """Initialize SSM client.
        
        Args:
            region_name: AWS region
            profile_name: AWS profile name (optional)
        """
        session = boto3.Session(profile_name=profile_name)
        self.ssm_client = session.client('ssm', region_name=region_name)
        self.region_name = region_name
    
    def get_change_calendar(self, calendar_name: str) -> Dict:
        """Get change calendar document.
        
        Args:
            calendar_name: Name of the change calendar
            
        Returns:
            Calendar document data
            
        Raises:
            ClientError: If calendar not found or access denied
        """
        try:
            # First try to get document description
            desc_response = self.ssm_client.describe_document(Name=calendar_name)
            
            # Then get the document content with TEXT format
            response = self.ssm_client.get_document(
                Name=calendar_name,
                DocumentFormat='TEXT'
            )
            
            # Combine description and content
            result = response.copy()
            result.update(desc_response['Document'])
            
            return result
        except ClientError as e:
            raise Exception(f"Failed to get calendar {calendar_name}: {e}")
    
    def list_change_calendars(self) -> List[Dict]:
        """List all change calendars in the account.
        
        Returns:
            List of calendar documents
        """
        try:
            response = self.ssm_client.list_documents(
                DocumentFilterList=[
                    {
                        'key': 'DocumentType',
                        'value': 'ChangeCalendar'
                    }
                ]
            )
            return response.get('DocumentIdentifiers', [])
        except ClientError as e:
            raise Exception(f"Failed to list Change Calendars: {e}")
    
    def get_calendar_state(self, calendar_name: str) -> str:
        """Get current state of change calendar.
        
        Args:
            calendar_name: Name of the change calendar
            
        Returns:
            Current state ('OPEN' or 'CLOSED')
        """
        try:
            response = self.ssm_client.get_calendar_state(
                CalendarNames=[calendar_name]
            )
            return response.get('State', 'UNKNOWN')
        except ClientError as e:
            raise Exception(f"Failed to get calendar state: {e}")
    
    def create_change_calendar(self, calendar_name: str, ics_content: str, tags: Optional[List[Dict]] = None) -> Dict:
        """Create a new Change Calendar with ICS content.
        
        Args:
            calendar_name: Name for the new calendar
            ics_content: ICS file content
            tags: Optional tags for the calendar
            
        Returns:
            Response from create_document API
            
        Raises:
            ClientError: If calendar creation fails
        """
        try:
            create_params = {
                'Content': ics_content,
                'Name': calendar_name,
                'DocumentType': 'ChangeCalendar',
                'DocumentFormat': 'TEXT'
            }
            
            if tags:
                create_params['Tags'] = tags
            
            response = self.ssm_client.create_document(**create_params)
            return response
        except ClientError as e:
            raise Exception(f"Failed to create Change Calendar {calendar_name}: {e}")
    
    def update_change_calendar(self, calendar_name: str, ics_content: str) -> Dict:
        """Update an existing Change Calendar with new ICS content.
        
        Args:
            calendar_name: Name of the existing calendar
            ics_content: New ICS file content
            
        Returns:
            Response from update_document API
            
        Raises:
            ClientError: If calendar update fails
        """
        try:
            response = self.ssm_client.update_document(
                Content=ics_content,
                Name=calendar_name,
                DocumentFormat='TEXT',
                DocumentVersion='$LATEST'
            )
            return response
        except ClientError as e:
            raise Exception(f"Failed to update Change Calendar {calendar_name}: {e}")
    
    def delete_change_calendar(self, calendar_name: str) -> Dict:
        """Delete a Change Calendar.
        
        Args:
            calendar_name: Name of the calendar to delete
            
        Returns:
            Response from delete_document API
            
        Raises:
            ClientError: If calendar deletion fails
        """
        try:
            response = self.ssm_client.delete_document(Name=calendar_name)
            return response
        except ClientError as e:
            raise Exception(f"Failed to delete Change Calendar {calendar_name}: {e}")
    
    def calendar_exists(self, calendar_name: str) -> bool:
        """Check if a Change Calendar exists.
        
        Args:
            calendar_name: Name of the calendar to check
            
        Returns:
            True if calendar exists, False otherwise
        """
        try:
            self.ssm_client.describe_document(Name=calendar_name)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'InvalidDocument':
                return False
            raise