"""
Tests for TokenManager class in burst download functionality.

This module contains tests for the TokenManager class which handles
automatic token refresh for authenticated API requests to CDSE.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from pathlib import Path

# Import directly from modules to avoid package-level imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import modules directly to avoid folium dependency in __init__.py
import phidown.downloader as downloader_module


class TestTokenManager:
    """Tests for TokenManager class."""
    
    def test_token_manager_initialization(self):
        """Test that TokenManager initializes with correct attributes."""
        token_mgr = downloader_module.TokenManager('user@example.com', 'password123')
        
        assert token_mgr.username == 'user@example.com'
        assert token_mgr.password == 'password123'
        assert token_mgr.access_token is None
        assert token_mgr.expiry <= time.time()
    
    def test_token_manager_custom_params(self):
        """Test TokenManager initialization with custom parameters."""
        custom_url = 'https://custom.token.url'
        custom_client = 'custom-client'
        
        token_mgr = downloader_module.TokenManager(
            'user@example.com', 
            'password123',
            token_url=custom_url,
            client_id=custom_client
        )
        
        assert token_mgr.token_url == custom_url
        assert token_mgr.client_id == custom_client

    def test_get_token_requires_username(self):
        with pytest.raises(ValueError, match='Username is required'):
            downloader_module.get_token('', 'password123')

    def test_get_token_requires_password(self):
        with pytest.raises(ValueError, match='Password is required'):
            downloader_module.get_token('user@example.com', '')
    
    @patch('phidown.downloader.requests.post')
    def test_refresh_access_token_success(self, mock_post):
        """Test successful token refresh."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'new_token_12345',
            'expires_in': 3600
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        token_mgr = downloader_module.TokenManager('user@example.com', 'password123')
        token_mgr.refresh_access_token()
        
        assert token_mgr.access_token == 'new_token_12345'
        assert token_mgr.expiry > time.time()
        
        # Verify the request was made with correct parameters
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert 'username' in call_args[1]['data']
        assert call_args[1]['data']['username'] == 'user@example.com'
        assert call_args[1]['data']['password'] == 'password123'
        assert call_args[1]['data']['grant_type'] == 'password'
        assert call_args[1]['timeout'] == downloader_module.REQUEST_TIMEOUT_SECONDS
    
    @patch('phidown.downloader.requests.post')
    def test_get_access_token_refreshes_when_expired(self, mock_post):
        """Test that get_access_token refreshes token when expired."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'new_token_67890',
            'expires_in': 3600
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        token_mgr = downloader_module.TokenManager('user@example.com', 'password123')
        token_mgr.expiry = time.time() - 100  # Set expiry to past
        
        token = token_mgr.get_access_token()
        
        assert token == 'new_token_67890'
        assert mock_post.call_count == 1
    
    @patch('phidown.downloader.requests.post')
    def test_get_access_token_reuses_valid_token(self, mock_post):
        """Test that get_access_token reuses valid token."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'valid_token',
            'expires_in': 3600
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        token_mgr = downloader_module.TokenManager('user@example.com', 'password123')
        
        # Get token first time
        token1 = token_mgr.get_access_token()
        
        # Get token second time - should reuse
        token2 = token_mgr.get_access_token()
        
        assert token1 == token2
        assert mock_post.call_count == 1  # Only called once
    
    @patch('phidown.downloader.requests.post')
    def test_token_expiry_buffer(self, mock_post):
        """Test that token expiry includes EXPIRY_BUFFER_SECONDS."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'test_token',
            'expires_in': 3600
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        token_mgr = downloader_module.TokenManager('user@example.com', 'password123')
        
        start_time = time.time()
        token_mgr.refresh_access_token()
        
        # Expiry should be approximately now + 3600 - EXPIRY_BUFFER_SECONDS
        buffer = downloader_module.TokenManager.EXPIRY_BUFFER_SECONDS
        expected_expiry = start_time + 3600 - buffer
        assert abs(token_mgr.expiry - expected_expiry) < 5  # Allow 5 second tolerance
    
    @patch('phidown.downloader.requests.post')
    def test_refresh_handles_missing_expires_in(self, mock_post):
        """Test that refresh handles missing expires_in with default value."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'test_token'
            # No expires_in field
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        token_mgr = downloader_module.TokenManager('user@example.com', 'password123')
        
        start_time = time.time()
        token_mgr.refresh_access_token()
        
        # Should use default 3600 seconds - EXPIRY_BUFFER_SECONDS
        buffer = downloader_module.TokenManager.EXPIRY_BUFFER_SECONDS
        expected_expiry = start_time + 3600 - buffer
        assert abs(token_mgr.expiry - expected_expiry) < 5


class TestDownloadBurstWithTokenManager:
    """Tests for download_burst_on_demand with TokenManager."""
    
    @patch('phidown.downloader.requests.post')
    def test_download_burst_with_token_manager(self, mock_post):
        """Test download_burst_on_demand works with TokenManager."""
        # Mock token refresh
        token_response = Mock()
        token_response.json.return_value = {
            'access_token': 'test_token_123',
            'expires_in': 3600
        }
        token_response.raise_for_status = Mock()
        
        # Mock burst download response
        burst_response = Mock()
        burst_response.status_code = 200
        burst_response.headers = {'Content-Disposition': 'filename=burst_test.zip'}
        burst_response.iter_content = Mock(return_value=[b'test_data'])
        
        # First call is token refresh, second is burst download
        mock_post.side_effect = [token_response, burst_response]
        
        token_mgr = downloader_module.TokenManager('user@example.com', 'password123')
        
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            downloader_module.download_burst_on_demand(
                burst_id='12345678-1234-1234-1234-123456789abc',
                token=token_mgr,
                output_dir=Path(tmpdir)
            )
            
            # Verify file was created
            output_file = Path(tmpdir) / 'burst_test.zip'
            assert output_file.exists()
            # Verify secure default
            assert mock_post.call_args_list[1].kwargs['verify'] is True
            assert mock_post.call_args_list[1].kwargs['timeout'] == downloader_module.REQUEST_TIMEOUT_SECONDS
    
    @patch('phidown.downloader.requests.post')
    def test_download_burst_with_string_token(self, mock_post):
        """Test download_burst_on_demand still works with string token."""
        # Mock burst download response
        burst_response = Mock()
        burst_response.status_code = 200
        burst_response.headers = {'Content-Disposition': 'filename=burst_test.zip'}
        burst_response.iter_content = Mock(return_value=[b'test_data'])
        
        mock_post.return_value = burst_response
        
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            downloader_module.download_burst_on_demand(
                burst_id='12345678-1234-1234-1234-123456789abc',
                token='static_token_string',
                output_dir=Path(tmpdir)
            )
            
            # Verify file was created
            output_file = Path(tmpdir) / 'burst_test.zip'
            assert output_file.exists()
            # Verify secure default
            assert mock_post.call_args.kwargs['verify'] is True
            assert mock_post.call_args.kwargs['timeout'] == downloader_module.REQUEST_TIMEOUT_SECONDS

    @patch('phidown.downloader.requests.post')
    def test_download_burst_insecure_opt_out_sets_verify_false(self, mock_post):
        """Test insecure_skip_verify opt-out sets verify=False."""
        burst_response = Mock()
        burst_response.status_code = 200
        burst_response.headers = {'Content-Disposition': 'filename=burst_test.zip'}
        burst_response.iter_content = Mock(return_value=[b'test_data'])
        mock_post.return_value = burst_response

        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            downloader_module.download_burst_on_demand(
                burst_id='12345678-1234-1234-1234-123456789abc',
                token='static_token_string',
                output_dir=Path(tmpdir),
                insecure_skip_verify=True
            )

            assert mock_post.call_args.kwargs['verify'] is False
            assert mock_post.call_args.kwargs['timeout'] == downloader_module.REQUEST_TIMEOUT_SECONDS
    
    @patch('phidown.downloader.requests.post')
    def test_download_burst_refreshes_token_on_redirect(self, mock_post):
        """Test that token is refreshed when following redirects."""
        # Mock token refresh
        token_response = Mock()
        token_response.json.return_value = {
            'access_token': 'test_token_456',
            'expires_in': 3600
        }
        token_response.raise_for_status = Mock()
        
        # Mock redirect response
        redirect_response = Mock()
        redirect_response.status_code = 302
        redirect_response.headers = {'Location': 'https://redirect.url'}
        
        # Mock final response
        final_response = Mock()
        final_response.status_code = 200
        final_response.headers = {'Content-Disposition': 'filename=burst_redirect.zip'}
        final_response.iter_content = Mock(return_value=[b'redirect_data'])
        
        # First call is token refresh (POST), 
        # second is initial burst request (POST, returns redirect 302),
        # third is redirected burst request (POST per downloader.py line 204)
        mock_post.side_effect = [token_response, redirect_response, final_response]
        
        token_mgr = downloader_module.TokenManager('user@example.com', 'password123')
        
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            downloader_module.download_burst_on_demand(
                burst_id='87654321-4321-4321-4321-123456789abc',
                token=token_mgr,
                output_dir=Path(tmpdir)
            )
            
            # Verify all 3 POST requests were made (token + initial + redirect)
            assert mock_post.call_count == 3
            # Verify both burst download calls are secure by default
            assert mock_post.call_args_list[1].kwargs['verify'] is True
            assert mock_post.call_args_list[2].kwargs['verify'] is True
            assert mock_post.call_args_list[1].kwargs['timeout'] == downloader_module.REQUEST_TIMEOUT_SECONDS
            assert mock_post.call_args_list[2].kwargs['timeout'] == downloader_module.REQUEST_TIMEOUT_SECONDS

    @patch('phidown.downloader.requests.post')
    def test_download_burst_redirect_keeps_insecure_verify_policy(self, mock_post):
        """Test insecure_skip_verify policy is preserved across redirect calls."""
        redirect_response = Mock()
        redirect_response.status_code = 302
        redirect_response.headers = {'Location': 'https://redirect.url'}

        final_response = Mock()
        final_response.status_code = 200
        final_response.headers = {'Content-Disposition': 'filename=burst_redirect.zip'}
        final_response.iter_content = Mock(return_value=[b'redirect_data'])

        mock_post.side_effect = [redirect_response, final_response]

        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            downloader_module.download_burst_on_demand(
                burst_id='87654321-4321-4321-4321-123456789abc',
                token='static_token_string',
                output_dir=Path(tmpdir),
                insecure_skip_verify=True
            )

            assert mock_post.call_count == 2
            assert mock_post.call_args_list[0].kwargs['verify'] is False
            assert mock_post.call_args_list[1].kwargs['verify'] is False
            assert mock_post.call_args_list[0].kwargs['timeout'] == downloader_module.REQUEST_TIMEOUT_SECONDS
            assert mock_post.call_args_list[1].kwargs['timeout'] == downloader_module.REQUEST_TIMEOUT_SECONDS


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
