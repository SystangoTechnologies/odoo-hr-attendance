# Copyright 2024 Moduon Team S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
from datetime import datetime, timedelta

from odoo import _, fields, models


class HrContract(models.Model):
    _inherit = "hr.contract"

    def _get_attendances(self):
        self.ensure_one()
        dtt_start = datetime.combine(self.date_start, datetime.min.time())
        dtt_end = datetime.combine(
            self.date_end or fields.Date.today(), datetime.min.time()
        )
        return self.employee_id.attendance_ids.filtered(
            lambda att: att.check_in >= dtt_start
            and att.check_in < (dtt_end + timedelta(days=1))
        )

    def action_update_overtime(self):
        """Open the wizard to preview and confirm overtime update."""
        # Filter to only valid contracts
        valid_contracts = self.filtered(lambda c: c.state in ("open", "close"))
        if not valid_contracts:
            return {"type": "ir.actions.act_window_close"}

        # Return wizard action with contract IDs in context
        return {
            "name": _("Update Overtime"),
            "type": "ir.actions.act_window",
            "res_model": "wizard.update.overtime",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_contract_ids": valid_contracts.ids,
                "active_ids": valid_contracts.ids,
            },
        }
