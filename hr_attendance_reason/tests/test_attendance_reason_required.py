# Copyright 2024 Systango
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import datetime

from odoo.exceptions import UserError
from odoo.tests import new_test_user
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DF

from odoo.addons.base.tests.common import BaseCommon


class TestHrAttendanceReasonRequired(BaseCommon):
    """Test required reason enforcement and default reason behavior."""

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
            {"name": "Late Arrival", "code": "LATE", "action_type": "sign_in"}
        )
        cls.att_reason_out = cls.att_reason_model.create(
            {"name": "Early Departure", "code": "EARLY", "action_type": "sign_out"}
        )
        cls.company = cls.employee.company_id

    def test_sign_out_blocked_without_reason(self):
        """TC1: Sign-out without reason raises UserError when required is enabled."""
        # Check in first
        attendance = self.employee.with_context(
            attendance_reason_id=self.att_reason_in.id
        )._attendance_action_change({})
        self.assertIn(self.att_reason_in, attendance.attendance_reason_ids)

        # Enable required reason on sign-out
        self.company.show_reason_on_attendance_screen = True
        self.company.required_reason_on_attendance_screen = True

        # Attempt sign-out without reason - should raise UserError
        with self.assertRaises(UserError) as cm:
            self.employee._attendance_action_change({})
        self.assertIn("An attendance reason is required for sign-out", str(cm.exception))

    def test_sign_out_with_reason_saved(self):
        """TC2: Sign-out with reason succeeds when required is enabled."""
        # Check in first
        attendance = self.employee.with_context(
            attendance_reason_id=self.att_reason_in.id
        )._attendance_action_change({})
        self.assertIn(self.att_reason_in, attendance.attendance_reason_ids)

        # Enable required reason on sign-out
        self.company.show_reason_on_attendance_screen = True
        self.company.required_reason_on_attendance_screen = True

        # Sign-out with reason - should succeed
        attendance = self.employee.with_context(
            attendance_reason_id=self.att_reason_out.id
        )._attendance_action_change({})
        self.assertEqual(len(attendance.attendance_reason_ids), 2)
        self.assertIn(self.att_reason_out, attendance.attendance_reason_ids)

    def test_default_reason_applied_on_sign_out(self):
        """TC3: Default sign-out reason is applied when optional and unselected."""
        # Check in first
        attendance = self.employee.with_context(
            attendance_reason_id=self.att_reason_in.id
        )._attendance_action_change({})
        self.assertIn(self.att_reason_in, attendance.attendance_reason_ids)

        # Enable reason but not required, set default
        self.company.show_reason_on_attendance_screen = True
        self.company.required_reason_on_attendance_screen = False
        self.company.reason_on_attendance_screen_default_sign_out = self.att_reason_out

        # Sign-out without selecting reason - should apply default
        attendance = self.employee._attendance_action_change({})
        self.assertIn(self.att_reason_out, attendance.attendance_reason_ids)

    def test_default_reason_applied_on_sign_in(self):
        """TC4: Default sign-in reason is applied when optional and unselected."""
        # Enable reason but not required, set default sign-in
        self.company.show_reason_on_attendance_screen = True
        self.company.required_reason_on_attendance_screen = False
        self.company.reason_on_attendance_screen_default_sign_in = self.att_reason_in

        # Sign-in without selecting reason - should apply default
        attendance = self.employee._attendance_action_change({})
        self.assertIn(self.att_reason_in, attendance.attendance_reason_ids)

    def test_multi_company_isolation(self):
        """TC5: Multi-company settings work independently."""
        # Create second company and employee
        company_b = self.env["res.company"].create({"name": "Company B"})
        company_b_att_reason_out = self.att_reason_model.with_company(company_b).create(
            {"name": "Company B Reason", "code": "COMPB", "action_type": "sign_out"}
        )
        user_b = new_test_user(
            self.env,
            login="test-user-b",
            groups="base.group_user,hr_attendance.group_hr_attendance_own_reader",
        )
        employee_b = self.env["hr.employee"].create(
            {"name": user_b.login, "user_id": user_b.id, "company_id": company_b.id}
        )

        # Configure Company A: required reason enabled
        self.company.show_reason_on_attendance_screen = True
        self.company.required_reason_on_attendance_screen = True

        # Configure Company B: required reason disabled, default set
        company_b.show_reason_on_attendance_screen = True
        company_b.required_reason_on_attendance_screen = False
        company_b.reason_on_attendance_screen_default_sign_out = company_b_att_reason_out

        # Check in both employees
        self.employee.with_context(
            attendance_reason_id=self.att_reason_in.id
        )._attendance_action_change({})
        employee_b.with_context(
            attendance_reason_id=self.att_reason_in.id
        )._attendance_action_change({})

        # Company A employee: sign-out without reason should raise error
        with self.assertRaises(UserError):
            self.employee._attendance_action_change({})

        # Company B employee: sign-out without reason should apply default
        attendance = employee_b._attendance_action_change({})
        self.assertIn(company_b_att_reason_out, attendance.attendance_reason_ids)

    def test_feature_disabled_behaves_as_before(self):
        """TC6: When feature disabled, behavior matches original."""
        # Ensure feature is disabled
        self.company.show_reason_on_attendance_screen = False

        # Check in without reason - should work
        attendance = self.employee._attendance_action_change({})
        self.assertEqual(len(attendance.attendance_reason_ids), 0)

        # Sign out without reason - should work
        attendance = self.employee._attendance_action_change({})
        self.assertEqual(len(attendance.attendance_reason_ids), 0)

        # Sign-in with explicit reason in context should still work
        # (backward compatibility for when reason is provided even with feature disabled)
        attendance = self.employee.with_context(
            attendance_reason_id=self.att_reason_in.id
        )._attendance_action_change({})
        self.assertIn(self.att_reason_in, attendance.attendance_reason_ids)

        # Sign-out with explicit reason should work
        attendance = self.employee.with_context(
            attendance_reason_id=self.att_reason_out.id
        )._attendance_action_change({})
        self.assertIn(self.att_reason_out, attendance.attendance_reason_ids)
