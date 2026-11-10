# Copyright 2024 Systango Technologies Pvt. Ltd.
# License LGPL-3 - See http://www.gnu.org/licenses/lgpl-3.0.html

{
    "name": "HR Attendance Reason Department",
    "version": "18.0.1.0.0",
    "category": "Human Resources",
    "website": "https://github.com/OCA/hr-attendance",
    "author": "Systango Technologies, Odoo Community Association (OCA)",
    "license": "LGPL-3",
    "installable": True,
    "depends": ["hr_attendance_reason"],
    "data": [
        "security/ir.model.access.csv",
        "views/hr_department_view.xml",
    ],
}
