{
    "name": "HR Attendance Absent Report",
    "version": "19.0.1.0.0",
    "category": "Human Resources/Attendance",
    "summary": "Report employees who were absent, on leave, on weekend, or on public holiday",
    "description": """
Absent Employees Report
=======================
Compute and list employees with no attendance for a selected period,
classifying each day as Absent, On Leave, Worked Time Off, Weekend,
or Public Holiday.
    """,
    "author": "Smart Station",
    "license": "LGPL-3",
    "depends": [
        "hr_attendance",
        "hr_holidays",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/hr_attendance_absent_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
}
