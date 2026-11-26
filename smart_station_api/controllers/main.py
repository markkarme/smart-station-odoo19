import logging
import functools
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class BaseAPIController(http.Controller):
    """Base controller with common API utilities."""

    def _get_token_from_header(self):
        """Extract JWT token from Authorization header."""
        auth_header = request.httprequest.headers.get('Authorization')
        if not auth_header:
            return None
        if not auth_header.startswith('Bearer '):
            return None
        return auth_header[7:]  # Remove 'Bearer ' prefix

    def _verify_token(self):
        """Verify token and return website user, or None if invalid."""
        token = self._get_token_from_header()
        if not token:
            return None

        website_user = request.env['api.access.token'].sudo().verify_token(token)
        return website_user if website_user else None

    def _get_request_info(self):
        """Get request IP and user agent."""
        return {
            'ip_address': request.httprequest.remote_addr,
            'user_agent': request.httprequest.headers.get('User-Agent', '')
        }

    def _success_response(self, data=None, message='Success', meta=None):
        """Standard success response format."""
        response = {
            'success': True,
            'message': message,
        }
        if data is not None:
            response['data'] = data
        if meta:
            response['meta'] = meta
        return response

    def _error_response(self, message, code=400, details=None):
        """Standard error response format."""
        response = {
            'success': False,
            'error': {
                'code': code,
                'message': message,
            }
        }
        if details:
            response['error']['details'] = details
        return response

    def _paginate(self, records, page=1, limit=20, order=None):
        """Paginate records and return meta information."""
        try:
            page = int(page) if page else 1
            limit = int(limit) if limit else 20
        except (TypeError, ValueError):
            page = 1
            limit = 20

        # Ensure reasonable limits
        page = max(1, page)
        limit = max(1, min(limit, 100))  # Max 100 items per page

        total = len(records) if isinstance(records, list) else records.search_count([])
        offset = (page - 1) * limit

        if isinstance(records, list):
            paginated = records[offset:offset + limit]
        else:
            paginated = records.search([], order=order, limit=limit, offset=offset) if order else records[offset:offset + limit]

        meta = {
            'page': page,
            'per_page': limit,
            'total': total,
            'pages': (total + limit - 1) // limit,  # Ceiling division
        }

        return paginated, meta

    def _get_employee_from_user(self, website_user=None):
        """Get employee record from website user."""
        website_user = website_user or request.env.context.get('website_user')
        if not website_user:
            return self.env['hr.employee']
        return website_user.employee_id

    def _has_permission(self, permission_code, website_user=None):
        """Check if website user has a specific permission."""
        website_user = website_user or request.env.context.get('website_user')
        if not website_user:
            return False
        
        # Get permissions from user's access rights
        permissions = website_user.get_permissions().get('permissions', {})
        return permissions.get(permission_code, False)

    def _is_admin(self, website_user=None):
        """Check if website user is admin."""
        return self._has_permission('is_admin', website_user)

    def _serialize_record(self, record, fields_list):
        """Serialize a single record with specified fields."""
        if not record:
            return None
        
        result = {}
        for field_name in fields_list:
            if '.' in field_name:
                # Handle relational fields like 'employee_id.name'
                parts = field_name.split('.')
                value = record
                for part in parts:
                    if value:
                        value = value[part]
                    else:
                        value = None
                        break
                result[field_name.replace('.', '_')] = value
            else:
                field = record._fields.get(field_name)
                value = record[field_name]
                
                if field and field.type == 'many2one':
                    result[field_name] = {
                        'id': value.id if value else None,
                        'name': value.display_name if value else None
                    }
                elif field and field.type in ('one2many', 'many2many'):
                    result[field_name] = [{'id': r.id, 'name': r.display_name} for r in value]
                elif field and field.type == 'datetime':
                    result[field_name] = value.isoformat() if value else None
                elif field and field.type == 'date':
                    result[field_name] = value.isoformat() if value else None
                else:
                    result[field_name] = value

        return result

    def _serialize_records(self, records, fields_list):
        """Serialize multiple records."""
        return [self._serialize_record(record, fields_list) for record in records]


def require_token(func):
    """Decorator to require valid API token."""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        controller = self if isinstance(self, BaseAPIController) else BaseAPIController()
        website_user = controller._verify_token()
        
        if not website_user:
            return controller._error_response('Unauthorized: Invalid or expired token', 401)
        
        # Add website_user to request context
        request.update_context(website_user=website_user)
        return func(self, *args, **kwargs)
    
    return wrapper


def require_admin(func):
    """Decorator to require admin permission."""
    @functools.wraps(func)
    @require_token
    def wrapper(self, *args, **kwargs):
        controller = self if isinstance(self, BaseAPIController) else BaseAPIController()
        
        if not controller._is_admin():
            return controller._error_response('Forbidden: Admin permission required', 403)
        
        return func(self, *args, **kwargs)
    
    return wrapper


def require_permission(permission_code):
    """Decorator to require specific permission."""
    def decorator(func):
        @functools.wraps(func)
        @require_token
        def wrapper(self, *args, **kwargs):
            controller = self if isinstance(self, BaseAPIController) else BaseAPIController()
            
            if not controller._has_permission(permission_code):
                return controller._error_response(
                    f'Forbidden: {permission_code} permission required', 
                    403
                )
            
            return func(self, *args, **kwargs)
        
        return wrapper
    return decorator
