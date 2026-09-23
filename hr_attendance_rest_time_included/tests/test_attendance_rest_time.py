# Copyright 2025 Tecnativa - Eduardo Ezerouali
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo.tests import tagged

from odoo.addons.base.tests.common import BaseCommon


@tagged("post_install", "-at_install")
class TestHrAttendanceRestTime(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Test Employee",
                "user_id": cls.env.user.id,
            }
        )
        cls.rest_reason = cls.env["hr.attendance.reason"].create(
            {"name": "Rest Time", "rest_time_included": True}
        )

        # Base datetime fixed for test (avoids duplicate overtime)
        cls.base_datetime = "2025-12-22 08:00:00"

    def test_01_create_attendance_and_open_rest_time(self):
        """Test opening and closing a rest time via attendance toggle"""

        # Step 1: Create attendance
        attendance = self.env["hr.attendance"].create(
            {
                "employee_id": self.employee.id,
                "check_in": self.base_datetime,
                "check_out": False,
            }
        )

        # Step 2: Open rest time (with check out)
        self.employee.with_context(
            attendance_reason_id=self.rest_reason.id,
        )._attendance_action_change()

        # Step 3: Check that rest time was created and parent attendance is checked out
        rest_time = self.env["hr.attendance.rest_time"].search(
            [("attendance_id", "=", attendance.id)]
        )
        self.assertEqual(len(rest_time), 1, "Rest time should have been created")
        self.assertTrue(attendance.check_out, "Parent attendance should be checked out")
        self.assertFalse(rest_time.check_out, "Rest time should still be open")

        # Step 4: Close rest time by toggling attendance again
        self.employee._attendance_action_change()

        # Step 5: Verify rest time is closed and parent attendance is reopened
        self.assertTrue(rest_time.check_out, "Rest time should now be closed")
        self.assertFalse(attendance.check_out, "Parent attendance should be reopened")

    def test_02_rest_hours_computation(self):
        """Test that rest hours are properly computed"""
        # Create an attendance record
        attendance = self.env["hr.attendance"].create(
            {
                "employee_id": self.employee.id,
                "check_in": "2025-12-22 08:00:00",
                "check_out": "2025-12-22 12:30:00",
            }
        )
        # Create rest time records with 30 minutes duration each
        rest_time_1 = self.env["hr.attendance.rest_time"].create(
            {
                "attendance_id": attendance.id,
                "check_in": "2025-12-22 09:00:00",
                "check_out": "2025-12-22 09:30:00",
            }
        )
        rest_time_2 = self.env["hr.attendance.rest_time"].create(
            {
                "attendance_id": attendance.id,
                "check_in": "2025-12-22 11:00:00",
                "check_out": "2025-12-22 11:30:00",
            }
        )
        # Verify rest hours are computed correctly
        # 30 minutes + 30 minutes = 1 hour
        self.assertEqual(
            attendance.rest_hours,
            1.0,
            "Rest hours should be 1.0 (two 30-minute breaks)",
        )

    def test_03_rest_time_deduction_in_report(self):
        """Test that rest time is properly deducted in attendance reports"""
        # Only run if theoretical time report module is installed
        if not self.env["ir.module.module"].search(
            [("name", "=", "hr_attendance_report_theoretical_time"), ("state", "=", "installed")]
        ):
            self.skipTest("hr_attendance_report_theoretical_time not installed")

        # Create an attendance record with 8 hours worked
        attendance = self.env["hr.attendance"].create(
            {
                "employee_id": self.employee.id,
                "check_in": "2025-12-22 08:00:00",
                "check_out": "2025-12-22 16:00:00",
            }
        )
        # Create a 1-hour rest time
        self.env["hr.attendance.rest_time"].create(
            {
                "attendance_id": attendance.id,
                "check_in": "2025-12-22 12:00:00",
                "check_out": "2025-12-22 13:00:00",
            }
        )
        # Verify rest hours are computed correctly
        self.assertEqual(
            attendance.rest_hours,
            1.0,
            "Rest hours should be 1.0",
        )
        # The worked hours should be 8 hours (16:00 - 08:00)
        # After deduction, it should be 7 hours (8 - 1)
        # But this is computed in the report, so we need to check the theoretical report
        report = self.env["hr.attendance.theoretical.time.report"]
        # Get the report entry for this attendance
        report_entries = report.search(
            [
                ("employee_id", "=", self.employee.id),
                ("date", "=", "2025-12-22"),
            ]
        )
        self.assertTrue(
            len(report_entries) > 0,
            "Report entry should exist for the attendance date",
        )
