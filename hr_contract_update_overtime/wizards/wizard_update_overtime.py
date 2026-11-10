# Copyright 2024 Moduon Team S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from datetime import datetime, timedelta

from odoo import _, fields, models


class WizardUpdateOvertime(models.TransientModel):
    _name = "wizard.update.overtime"
    _description = "Update Overtime Wizard"

    contract_ids = fields.Many2many(
        comodel_name="hr.contract",
        string="Contracts",
        required=True,
        readonly=True,
        domain=[("state", "in", ("open", "close"))],
        help="Contracts to update overtime for",
    )
    employee_ids = fields.Many2many(
        comodel_name="hr.employee",
        string="Employees",
        readonly=True,
        compute="_compute_employee_info",
        store=True,
        help="Employees affected by the overtime update",
    )
    date_start = fields.Date(
        string="Start Date",
        readonly=True,
        help="Start date from the selected contracts",
    )
    date_end = fields.Date(
        string="End Date",
        readonly=True,
        help="End date from the selected contracts",
    )
    overtime_days_count = fields.Integer(
        string="Overtime Days",
        readonly=True,
        compute="_compute_employee_info",
        store=True,
        help="Number of distinct attendance days that will have overtime recomputed",
    )

    def default_get(self, fields_list):
        """Set default values for wizard based on active contracts from context."""
        res = super().default_get(fields_list)
        active_ids = self._context.get("active_ids")
        if active_ids:
            contracts = self.env["hr.contract"].browse(active_ids)
            # Filter to only valid contracts
            valid_contracts = contracts.filtered(
                lambda c: c.state in ("open", "close")
            )
            if valid_contracts:
                res["contract_ids"] = [(6, 0, valid_contracts.ids)]
                # Compute date range across all contracts
                dates = []
                for contract in valid_contracts:
                    if contract.date_start:
                        dates.append(contract.date_start)
                    if contract.date_end:
                        dates.append(contract.date_end)
                if dates:
                    res["date_start"] = min(dates)
                    res["date_end"] = (
                        max(dates)
                        if any(c.date_end for c in valid_contracts)
                        else fields.Date.today()
                    )
        return res

    def _compute_employee_info(self):
        """Compute employee list and overtime days count."""
        for wizard in self:
            # Get unique employees from contracts
            wizard.employee_ids = wizard.contract_ids.mapped("employee_id")

            # Count distinct attendance days across all contracts
            all_attendances = self.env["hr.attendance"].browse()
            for contract in wizard.contract_ids:
                attendances = contract._get_attendances()
                all_attendances |= attendances

            # Count distinct attendance days
            distinct_days = set()
            for attendance in all_attendances:
                attendance_date = attendance.check_in.date()
                distinct_days.add(attendance_date)

            wizard.overtime_days_count = len(distinct_days)

    def action_confirm(self):
        """Execute the overtime update for all selected contracts."""
        self.ensure_one()
        for contract in self.contract_ids:
            # Get attendances and update overtime
            attendances = contract._get_attendances()
            attendances._update_overtime()
            # Post message on contract
            contract.message_post(
                body=_("Overtime updated"),
                subtype_xmlid="mail.mt_note",
                message_type="comment",
                author_id=self.env.user.partner_id.id,
            )
        return {"type": "ir.actions.act_window_close"}
