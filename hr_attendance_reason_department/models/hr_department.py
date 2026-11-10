# Copyright 2024 Systango Technologies Pvt. Ltd.
# License LGPL-3 - See http://www.gnu.org/licenses/lgpl-3.0.html

from odoo import fields, models


class HrDepartment(models.Model):
    _inherit = "hr.department"

    default_sign_in_reason_id = fields.Many2one(
        "hr.attendance.reason",
        string="Default sign-in reason",
        domain=[
            ("action_type", "=", "sign_in"),
            ("show_on_attendance_screen", "=", True),
        ],
        check_company=True,
    )
    default_sign_out_reason_id = fields.Many2one(
        "hr.attendance.reason",
        string="Default sign-out reason",
        domain=[
            ("action_type", "=", "sign_out"),
            ("show_on_attendance_screen", "=", True),
        ],
        check_company=True,
    )
