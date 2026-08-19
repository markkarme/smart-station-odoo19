{
    "name": "Attendance Location Portal",
    "version": "19.0.1.3.5",
    "category": "Human Resources/Attendance",
    "summary": "Geo-fenced employee attendance from portal",
    "description": """
Configure attendance locations with Google Maps links and allowed range in meters.
Employees can check in and check out from the portal only when they are inside
the allowed distance from a configured attendance location.
    """,
    "author": "CUC",
    "license": "LGPL-3",
    "depends": ["hr_attendance", "hr_holidays", "mail", "portal", "website"],
    "data": [
        
        "data/mail_activity_data.xml",
        "security/hr_general_request_security.xml",
        "security/hr_attendance_adjustment_request_security.xml",
        "security/ir.model.access.csv",
        "views/hr_general_request_views.xml",
        "views/hr_attendance_adjustment_request_views.xml",
        "views/attendance_location_views.xml",
        "views/hr_employee_views.xml",
        "views/hr_attendance_views.xml",
        "views/portal_templates.xml",
        "views/portal_time_off_templates.xml",
        "views/portal_allocation_templates.xml",
        "views/portal_general_request_templates.xml",
        "views/portal_attendance_adjustment_templates.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "attendance_location_portal/static/src/js/activity_menu_patch.js",
        ],
        "web.assets_frontend": [
            "attendance_location_portal/static/src/css/portal_attendance.css",
            "attendance_location_portal/static/src/js/portal_attendance.js",
            "attendance_location_portal/static/src/css/portal_time_off.css",
            "attendance_location_portal/static/src/js/portal_time_off.js",
            "attendance_location_portal/static/src/js/portal_allocation.js",
        ],
    },
    "installable": True,
    "application": False,
}
