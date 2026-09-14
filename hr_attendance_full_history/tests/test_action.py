# Copyright 2026 Moduon Team S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests import new_test_user, users

from odoo.addons.base.tests.common import BaseCommon


class TestResUsers(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.attendance_user = new_test_user(
            cls.env,
            login="attendance-history-user",
            groups="base.group_user,hr_attendance.group_hr_attendance_own_reader",
        )
        cls.employee = cls.env["hr.employee"].create(
            {"name": cls.attendance_user.login, "user_id": cls.attendance_user.id}
        )
        now = fields.Datetime.now()
        cls.today_check_in = now.replace(hour=8, minute=0, second=0, microsecond=0)
        cls.last_month_check_in = cls.today_check_in - relativedelta(months=1)

    def test_action_open_last_month_attendances(self):
        """Check that the action is modified as expected."""
        action = self.env.user.action_open_last_month_attendances()
        # Check that the hard domain for check_in is NOT there
        for domain_item in action["domain"]:
            self.assertNotEqual(
                domain_item[:2],
                ("check_in", ">="),
                "Domain for 'check_in' should not exist",
            )
        # The context now contains the search default
        self.assertTrue(action["context"]["search_default_filter_this_month"])

    @users("attendance-history-user")
    def test_last_month_attendances_visible_after_filter_removed(self):
        """FH-1: older attendances appear once the This month chip is removed."""
        attendance_model = self.env["hr.attendance"]
        employee = self.env.user.employee_id
        last_month, today = (
            attendance_model.sudo()
            .create(
                [
                    {
                        "employee_id": employee.id,
                        "check_in": self.last_month_check_in,
                        "check_out": self.last_month_check_in
                        + relativedelta(hours=8),
                    },
                    {
                        "employee_id": employee.id,
                        "check_in": self.today_check_in,
                        "check_out": self.today_check_in + relativedelta(hours=8),
                    },
                ]
            )
        )
        action = self.env.user.action_open_last_month_attendances()
        this_month_domain = [
            (
                "check_in",
                ">=",
                fields.Datetime.now().replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0
                ),
            )
        ]
        with_filter = attendance_model.search(action["domain"] + this_month_domain)
        self.assertIn(today, with_filter)
        self.assertNotIn(last_month, with_filter)
        without_filter = attendance_model.search(action["domain"])
        self.assertIn(today, without_filter)
        self.assertIn(last_month, without_filter)
