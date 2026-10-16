# Copyright 2025 Systango Technologies
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "HR Attendance Employee Filter",
    "summary": """
        Add a predefined Employee filter to the Attendance search view""",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "Systango Technologies, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/hr-attendance",
    "category": "Human Resources",
    "depends": ["hr_attendance"],
    "data": [
        "views/hr_attendance_views.xml",
    ],
    "installable": True,
}
