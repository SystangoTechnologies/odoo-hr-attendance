# Copyright 2023 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models
from odoo.exceptions import UserError


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def _attendance_action_change(self, geo_information=None):
        # Determine the action type (sign-in or sign-out) before the action
        # An employee is signing out if they were checked in before the action
        was_checked_in = self and self[0].attendance_state == "checked_in"
        is_sign_out = was_checked_in

        # Call super to create/update the attendance record
        attendance = super()._attendance_action_change(geo_information=geo_information)

        # Only apply reason logic if the feature is enabled for this company
        if self and self[0].company_id.show_reason_on_attendance_screen:
            employee = self[0]
            reason_id = self.env.context.get("attendance_reason_id")
            company = employee.company_id

            if is_sign_out:
                # Sign-out validation: require reason if required_reason_on_attendance_screen is True
                if company.required_reason_on_attendance_screen and not reason_id:
                    raise UserError("An attendance reason is required for sign-out.")
                # Apply default reason if not provided and not required
                if not reason_id and company.reason_on_attendance_screen_default_sign_out:
                    reason_id = company.reason_on_attendance_screen_default_sign_out.id
            else:
                # Sign-in: apply default reason if configured and not provided
                if not reason_id and company.reason_on_attendance_screen_default_sign_in:
                    reason_id = company.reason_on_attendance_screen_default_sign_in.id

            # Write the reason to the attendance record
            if reason_id:
                attendance.attendance_reason_ids = [(4, reason_id)]
        elif self.env.context.get("attendance_reason_id"):
            # Feature disabled, but reason was provided in context (backward compatibility)
            attendance.attendance_reason_ids = [(4, self.env.context.get("attendance_reason_id"))]

        return attendance
