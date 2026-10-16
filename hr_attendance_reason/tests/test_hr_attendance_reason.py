# Copyright 2017 Odoo S.A.
# Copyright 2018 ForgeFlow, S.L.
# Copyright 2023 Tecnativa - Víctor Martínez
# License LGPL-3 - See http://www.gnu.org/licenses/lgpl-3.0.html

from datetime import datetime, timedelta

from odoo.tests import new_test_user, users
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DF

from odoo.addons.base.tests.common import BaseCommon


class TestHrAttendanceReason(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.att_reason_model = cls.env["hr.attendance.reason"]
        cls.user = new_test_user(
            cls.env,
            login="test-user",
            groups="base.group_user,hr_attendance.group_hr_attendance_own_reader",
        )
        cls.employee = cls.env["hr.employee"].create(
            {"name": cls.user.login, "user_id": cls.user.id}
        )
        cls.att_reason_in = cls.att_reason_model.create(
            {"name": "Bus did not come", "code": "BB", "action_type": "sign_in"}
        )
        cls.att_reason_out = cls.att_reason_model.create(
            {"name": "A lot of work", "code": "WORK", "action_type": "sign_out"}
        )

    @users("test-user")
    def test_employee_edit(self):
        self.env["hr.attendance"].sudo().create(
            {
                "employee_id": self.env.user.employee_id.id,
                "check_in": datetime.now().strftime(DF),
                "attendance_reason_ids": [(4, self.att_reason_in.id)],
            }
        )
        # check out
        attendance = self.env.user.employee_id.with_context(
            attendance_reason_id=self.att_reason_out.id
        )._attendance_action_change({})
        self.assertIn(self.att_reason_in, attendance.attendance_reason_ids)
        self.assertIn(self.att_reason_out, attendance.attendance_reason_ids)

    @users("test-user")
    def test_user_attendance_manual(self):
        # check in
        attendance = self.env.user.employee_id.with_context(
            attendance_reason_id=self.att_reason_in.id
        )._attendance_action_change({})
        self.assertIn(self.att_reason_in, attendance.attendance_reason_ids)
        # check out
        attendance = self.env.user.employee_id.with_context(
            attendance_reason_id=self.att_reason_out.id
        )._attendance_action_change({})
        self.assertIn(self.att_reason_out, attendance.attendance_reason_ids)


class TestHrAttendanceMissingCheckout(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(
            cls.env,
            login="test-user-checkout",
            groups="base.group_user,hr_attendance.group_hr_attendance_own_reader",
        )
        cls.employee = cls.env["hr.employee"].create(
            {"name": cls.user.login, "user_id": cls.user.id}
        )
        cls.attendance_model = cls.env["hr.attendance"]

    def test_incomplete_attendance_identified(self):
        """Test that incomplete attendance records are identified."""
        now = datetime.now()
        incomplete = self.attendance_model.create(
            {
                "employee_id": self.employee.id,
                "check_in": now.strftime(DF),
            }
        )
        self.assertTrue(incomplete.is_missing_checkout)

    def test_complete_attendance_not_marked(self):
        """Test that complete attendance records are not marked as missing checkout."""
        now = datetime.now()
        checkout_time = now + timedelta(hours=8)
        complete = self.attendance_model.create(
            {
                "employee_id": self.employee.id,
                "check_in": now.strftime(DF),
                "check_out": checkout_time.strftime(DF),
            }
        )
        self.assertFalse(complete.is_missing_checkout)

    def test_filter_missing_checkout(self):
        """Test that the missing checkout filter works correctly."""
        now = datetime.now()

        # Create an incomplete record
        incomplete = self.attendance_model.create(
            {
                "employee_id": self.employee.id,
                "check_in": now.strftime(DF),
            }
        )

        # Create a complete record
        self.attendance_model.create(
            {
                "employee_id": self.employee.id,
                "check_in": (now - timedelta(days=1)).strftime(DF),
                "check_out": (now - timedelta(days=1) + timedelta(hours=8)).strftime(
                    DF
                ),
            }
        )

        # Apply the filter for missing checkout
        filtered = self.attendance_model.search(
            [("check_in", "!=", False), ("check_out", "=", False)]
        )

        self.assertIn(incomplete, filtered)
        self.assertEqual(len(filtered), 1)

    def test_no_checkout_field_computation(self):
        """Test that is_missing_checkout is computed correctly on update."""
        now = datetime.now()
        attendance = self.attendance_model.create(
            {
                "employee_id": self.employee.id,
                "check_in": now.strftime(DF),
            }
        )

        # Initially, should be missing checkout
        self.assertTrue(attendance.is_missing_checkout)

        # After adding checkout, should not be missing checkout
        attendance.write({"check_out": (now + timedelta(hours=8)).strftime(DF)})
        self.assertFalse(attendance.is_missing_checkout)
