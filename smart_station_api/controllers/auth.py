import logging
from odoo import http
from odoo.http import request
from .main import BaseAPIController, require_token

_logger = logging.getLogger(__name__)


class AuthAPIController(BaseAPIController):
    """Authentication endpoints for API using website.user."""

    @http.route('/api/v1/auth/login', type='jsonrpc', auth='public', methods=['POST'], csrf=False, cors='*')
    def login(self, **kwargs):
        """
        Login endpoint for website users.
        
        Expected payload:
        {
            "login": "user@example.com",
            "password": "password123",
            "device_id": "optional-device-id",
            "device_name": "optional-device-name"
        }
        """
        try:
            login = kwargs.get('login')
            password = kwargs.get('password')
            device_id = kwargs.get('device_id')
            device_name = kwargs.get('device_name')

            if not login or not password:
                return self._error_response('Login and password are required', 400)

            # Authenticate website user
            website_user = request.env['website.user'].sudo().authenticate(login, password)
            if not website_user:
                return self._error_response('Invalid credentials', 401)

            # Check if user is active
            if not website_user.active:
                return self._error_response('User account is disabled', 403)

            # Get request info
            req_info = self._get_request_info()

            # Generate refresh token
            refresh_token = request.env['api.refresh.token'].sudo().generate_token(
                website_user_id=website_user.id,
                device_id=device_id,
                device_name=device_name,
                ip_address=req_info['ip_address'],
                user_agent=req_info['user_agent']
            )

            # Generate access token
            access_token = request.env['api.access.token'].sudo().generate_token(
                website_user_id=website_user.id,
                ip_address=req_info['ip_address'],
                user_agent=req_info['user_agent'],
                refresh_token_id=refresh_token.id
            )

            # Get user permissions
            user_data = website_user.get_permissions()

            return self._success_response(
                data={
                    'access_token': access_token.token,
                    'refresh_token': refresh_token.token,
                    'expires_in': 3600,  # 1 hour in seconds
                    'token_type': 'Bearer',
                    'user': user_data,
                },
                message='Login successful'
            )

        except Exception as e:
            _logger.exception('Login error: %s', str(e))
            return self._error_response('Login failed', 500, {'error': str(e)})

    @http.route('/api/v1/auth/refresh', type='jsonrpc', auth='public', methods=['POST'], csrf=False, cors='*')
    def refresh_token(self, **kwargs):
        """
        Refresh access token using refresh token.
        
        Expected payload:
        {
            "refresh_token": "refresh_token_here"
        }
        """
        try:
            refresh_token_str = kwargs.get('refresh_token')
            if not refresh_token_str:
                return self._error_response('Refresh token is required', 400)

            # Verify refresh token
            refresh_token = request.env['api.refresh.token'].sudo().verify_token(refresh_token_str)
            if not refresh_token:
                return self._error_response('Invalid or expired refresh token', 401)

            # Check if user is still active
            if not refresh_token.website_user_id.active:
                return self._error_response('User account is disabled', 403)

            # Get request info
            req_info = self._get_request_info()

            # Generate new access token
            access_token = request.env['api.access.token'].sudo().generate_token(
                website_user_id=refresh_token.website_user_id.id,
                ip_address=req_info['ip_address'],
                user_agent=req_info['user_agent'],
                refresh_token_id=refresh_token.id
            )

            return self._success_response(
                data={
                    'access_token': access_token.token,
                    'expires_in': 3600,  # 1 hour in seconds
                    'token_type': 'Bearer',
                },
                message='Token refreshed successfully'
            )

        except Exception as e:
            _logger.exception('Token refresh error: %s', str(e))
            return self._error_response('Token refresh failed', 500, {'error': str(e)})

    @http.route('/api/v1/auth/logout', type='jsonrpc', auth='public', methods=['POST'], csrf=False, cors='*')
    @require_token
    def logout(self, **kwargs):
        """
        Logout and invalidate tokens.
        
        Optional payload:
        {
            "refresh_token": "refresh_token_to_invalidate"
        }
        """
        try:
            website_user = request.env.context.get('website_user')
            if not website_user:
                return self._error_response('User not authenticated', 401)

            token = self._get_token_from_header()

            # Invalidate current access token
            if token:
                access_token = request.env['api.access.token'].sudo().search([
                    ('token', '=', token),
                    ('website_user_id', '=', website_user.id)
                ], limit=1)
                if access_token:
                    access_token.invalidate()

            # Invalidate refresh token if provided
            refresh_token_str = kwargs.get('refresh_token')
            if refresh_token_str:
                refresh_token = request.env['api.refresh.token'].sudo().search([
                    ('token', '=', refresh_token_str),
                    ('website_user_id', '=', website_user.id)
                ], limit=1)
                if refresh_token:
                    refresh_token.invalidate()

            return self._success_response(message='Logout successful')

        except Exception as e:
            _logger.exception('Logout error: %s', str(e))
            return self._error_response('Logout failed', 500, {'error': str(e)})

    @http.route('/api/v1/auth/me', type='jsonrpc', auth='public', methods=['POST'], csrf=False, cors='*')
    @require_token
    def get_current_user(self, **kwargs):
        """Get current authenticated user information."""
        try:
            website_user = request.env.context.get('website_user')
            if not website_user:
                return self._error_response('User not authenticated', 401)

            user_data = website_user.get_permissions()
            
            return self._success_response(
                data=user_data,
                message='User information retrieved successfully'
            )

        except Exception as e:
            _logger.exception('Get user error: %s', str(e))
            return self._error_response('Failed to get user information', 500, {'error': str(e)})

    @http.route('/api/v1/auth/validate', type='jsonrpc', auth='public', methods=['POST'], csrf=False, cors='*')
    @require_token
    def validate_token(self, **kwargs):
        """Validate if current token is valid."""
        return self._success_response(
            data={'valid': True},
            message='Token is valid'
        )
