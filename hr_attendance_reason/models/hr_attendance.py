# Copyright 2017 Odoo S.A.
# Copyright 2018 ForgeFlow, S.L.
# License LGPL-3 - See http://www.gnu.org/licenses/lgpl-3.0.html

from odoo import api, fields, models


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    attendance_reason_ids = fields.Many2many(
        comodel_name="hr.attendance.reason",
        string="Attendance Reason",
        help="Specifies the reason for signing In/signing Out in case of "
        "less or extra hours.",
    )
    is_missing_checkout = fields.Boolean(
        string="Missing Check-Out",
        compute="_compute_is_missing_checkout",
        store=True,
        help="Indicates if this attendance record has a check-in but no check-out.",
    )

    @api.depends("check_in", "check_out")
    def _compute_is_missing_checkout(self):
        """Compute if the attendance record is missing a check-out."""
        for record in self:
            record.is_missing_checkout = record.check_in and not record.check_out
