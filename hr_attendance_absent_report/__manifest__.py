{
    "name": "HR Attendance Absent Report",
    "version": "19.0.1.1.3",
    "category": "Human Resources/Attendance",
    "summary": "Report employees who were absent, on leave, on weekend, or on public holiday",
    "description": """
Absent Employees Report
=======================
Compute and list employees with no attendance for a selected period,
classifying each day as Absent, On Leave, Worked Time Off, Weekend,
or Public Holiday.

Portal Admin users can open the same report from /my/absent_employees,
limited to their allowed companies.
    """,
    "author": "Smart Station",
    "license": "LGPL-3",
    "depends": [
        "hr_attendance",
        "hr_holidays",
        "portal",
        "attendance_location_portal",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/hr_attendance_absent_wizard_views.xml",
        "views/portal_absent_templates.xml",
    ],
    "installable": True,
    "application": False,
}
