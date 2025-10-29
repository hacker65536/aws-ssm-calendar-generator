"""
Unit tests for AWS Client functionality.
"""

import pytest
from unittest.mock import Mock, patch
import json
from botocore.exceptions import ClientError, NoCredentialsError

from src.aws_client import AWSClient, AWSClientError


class TestAWSClient:
    """Test cases for AWSClient class."""

    @patch('boto3.client')
    def test_init_with_default_region(self, mock_boto_client):
        """Test initialization with default region."""
        client = AWSClient()
        
        assert client.region == 'us-east-1'
        mock_boto_client.assert_called_with('ssm', region_name='us-east-1')

    @patch('boto3.client')
    def test_init_with_custom_region(self, mock_boto_client):
        """Test initialization with custom region."""
        client = AWSClient(region='ap-northeast-1')
        
        assert client.region == 'ap-northeast-1'
        mock_boto_client.assert_called_with('ssm', region_name='ap-northeast-1')

    @patch('boto3.client')
    def test_init_with_profile(self, mock_boto_client):
        """Test initialization with AWS profile."""
        with patch('boto3.Session') as mock_session:
            mock_session_instance = Mock()
            mock_session.return_value = mock_session_instance
            
            client = AWSClient(profile='test-profile')
            
            mock_session.assert_called_with(profile_name='test-profile')

    @patch('boto3.client')
    def test_get_change_calendar_success(self, mock_boto_client):
        """Test successful Change Calendar retrieval."""
        mock_client = Mock()
        mock_client.get_document.return_value = {
            'Content': json.dumps({
                'name': 'test-calendar',
                'events': []
            })
        }
        mock_boto_client.return_value = mock_client
        
        client = AWSClient()
        result = client.get_change_calendar('test-calendar')
        
        assert 'name' in result
        assert result['name'] == 'test-calendar'
        mock_client.get_document.assert_called_once_with(Name='test-calendar')

    @patch('boto3.client')
    def test_get_change_calendar_not_found(self, mock_boto_client):
        """Test Change Calendar not found error."""
        mock_client = Mock()
        mock_client.get_document.side_effect = ClientError(
            {'Error': {'Code': 'DocumentNotFound'}},
            'GetDocument'
        )
        mock_boto_client.return_value = mock_client
        
        client = AWSClient()
        
        with pytest.raises(AWSClientError):
            client.get_change_calendar('non-existent-calendar')

    @patch('boto3.client')
    def test_get_change_calendar_access_denied(self, mock_boto_client):
        """Test Change Calendar access denied error."""
        mock_client = Mock()
        mock_client.get_document.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied'}},
            'GetDocument'
        )
        mock_boto_client.return_value = mock_client
        
        client = AWSClient()
        
        with pytest.raises(AWSClientError):
            client.get_change_calendar('restricted-calendar')

    @patch('boto3.client')
    def test_list_change_calendars_success(self, mock_boto_client):
        """Test successful Change Calendar listing."""
        mock_client = Mock()
        mock_client.list_documents.return_value = {
            'DocumentIdentifiers': [
                {
                    'Name': 'calendar-1',
                    'DocumentType': 'ChangeCalendar'
                },
                {
                    'Name': 'calendar-2',
                    'DocumentType': 'ChangeCalendar'
                }
            ]
        }
        mock_boto_client.return_value = mock_client
        
        client = AWSClient()
        calendars = client.list_change_calendars()
        
        assert len(calendars) == 2
        assert calendars[0]['Name'] == 'calendar-1'
        assert calendars[1]['Name'] == 'calendar-2'

    @patch('boto3.client')
    def test_list_change_calendars_empty(self, mock_boto_client):
        """Test Change Calendar listing with no results."""
        mock_client = Mock()
        mock_client.list_documents.return_value = {
            'DocumentIdentifiers': []
        }
        mock_boto_client.return_value = mock_client
        
        client = AWSClient()
        calendars = client.list_change_calendars()
        
        assert len(calendars) == 0

    @patch('boto3.client')
    def test_get_calendar_state_open(self, mock_boto_client):
        """Test getting calendar state when open."""
        mock_client = Mock()
        mock_client.get_calendar_state.return_value = {
            'State': 'OPEN',
            'AtTime': '2024-01-01T00:00:00Z'
        }
        mock_boto_client.return_value = mock_client
        
        client = AWSClient()
        state = client.get_calendar_state('test-calendar')
        
        assert state['State'] == 'OPEN'
        assert 'AtTime' in state

    @patch('boto3.client')
    def test_get_calendar_state_closed(self, mock_boto_client):
        """Test getting calendar state when closed."""
        mock_client = Mock()
        mock_client.get_calendar_state.return_value = {
            'State': 'CLOSED',
            'AtTime': '2024-01-01T00:00:00Z'
        }
        mock_boto_client.return_value = mock_client
        
        client = AWSClient()
        state = client.get_calendar_state('test-calendar')
        
        assert state['State'] == 'CLOSED'

    @patch('boto3.client')
    def test_credentials_error(self, mock_boto_client):
        """Test handling of credentials error."""
        mock_boto_client.side_effect = NoCredentialsError()
        
        with pytest.raises(AWSClientError):
            AWSClient()

    @patch('boto3.client')
    def test_create_change_calendar(self, mock_boto_client):
        """Test creating a new Change Calendar."""
        mock_client = Mock()
        mock_client.create_document.return_value = {
            'DocumentDescription': {
                'Name': 'new-calendar',
                'Status': 'Creating'
            }
        }
        mock_boto_client.return_value = mock_client
        
        client = AWSClient()
        result = client.create_change_calendar(
            'new-calendar',
            'Test Calendar',
            'DEFAULT_OPEN'
        )
        
        assert result['DocumentDescription']['Name'] == 'new-calendar'
        mock_client.create_document.assert_called_once()

    @patch('boto3.client')
    def test_update_change_calendar(self, mock_boto_client):
        """Test updating an existing Change Calendar."""
        mock_client = Mock()
        mock_client.update_document.return_value = {
            'DocumentDescription': {
                'Name': 'existing-calendar',
                'Status': 'Updating'
            }
        }
        mock_boto_client.return_value = mock_client
        
        client = AWSClient()
        calendar_content = {'events': []}
        
        result = client.update_change_calendar('existing-calendar', calendar_content)
        
        assert result['DocumentDescription']['Name'] == 'existing-calendar'
        mock_client.update_document.assert_called_once()

    @patch('boto3.client')
    def test_delete_change_calendar(self, mock_boto_client):
        """Test deleting a Change Calendar."""
        mock_client = Mock()
        mock_client.delete_document.return_value = {}
        mock_boto_client.return_value = mock_client
        
        client = AWSClient()
        result = client.delete_change_calendar('calendar-to-delete')
        
        assert result == {}
        mock_client.delete_document.assert_called_once_with(Name='calendar-to-delete')

    @patch('boto3.client')
    def test_validate_credentials(self, mock_boto_client):
        """Test credential validation."""
        mock_client = Mock()
        mock_client.get_caller_identity.return_value = {
            'Account': '123456789012',
            'UserId': 'test-user',
            'Arn': 'arn:aws:iam::123456789012:user/test-user'
        }
        
        # Mock STS client for credential validation
        with patch('boto3.client') as mock_sts_client:
            mock_sts_client.return_value = mock_client
            
            client = AWSClient()
            is_valid = client.validate_credentials()
            
            assert is_valid is True

    @patch('boto3.client')
    def test_validate_credentials_invalid(self, mock_boto_client):
        """Test credential validation with invalid credentials."""
        mock_client = Mock()
        mock_client.get_caller_identity.side_effect = ClientError(
            {'Error': {'Code': 'InvalidUserID.NotFound'}},
            'GetCallerIdentity'
        )
        
        with patch('boto3.client') as mock_sts_client:
            mock_sts_client.return_value = mock_client
            
            client = AWSClient()
            is_valid = client.validate_credentials()
            
            assert is_valid is False