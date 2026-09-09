# Copyright 2026 Moduon Team S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import models


class ResUsers(models.Model):
    _inherit = "res.users"

    def action_open_last_month_attendances(self):
        result = super().action_open_last_month_attendances()
        result["context"]["search_default_filter_this_month"] = True
        return result
