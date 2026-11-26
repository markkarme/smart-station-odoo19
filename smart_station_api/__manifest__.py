{
    'name': 'Smart Station API',
    'version': '19.0.2.0.0',
    'category': 'API',
    'summary': 'REST API for Smart Station Portal Features with Separate User Management',
    'description': '''
        Provides REST API endpoints for external applications (React/Vue).
        
        Features:
        - Separate Website User Management
        - Configurable Access Rights
        - JWT Authentication
        - Attendance management API
        - Leave/Time off API
        - General requests API
        - Attendance adjustments API
        - Employee management API
        
        User Management:
        - Create website users from employees
        - Configure access rights per user
        - Control permissions from Odoo
        - Independent from Odoo portal users
    ''',
    'author': 'Smart Station',
    'website': 'https://www.smartstation.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'hr',
        'hr_attendance',
        'attendance_location_portal',
        'hr_attendance_absent_report',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/api_config_data.xml',
        'data/default_access_rights_data.xml',
        'views/dashboard_views.xml',
        'views/api_token_views.xml',
        'views/website_user_views.xml',
        'views/website_access_right_views.xml',
        'views/hr_employee_views.xml',
        'views/wizard_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
