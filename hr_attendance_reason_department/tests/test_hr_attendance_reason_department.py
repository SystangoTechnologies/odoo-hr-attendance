# Copyright 2024 Systango Technologies Pvt. Ltd.
# License LGPL-3 - See http://www.gnu.org/licenses/lgpl-3.0.html

from odoo.tests import new_test_user, users

from odoo.addons.base.tests.common import BaseCommon


class TestHrAttendanceReasonDepartment(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.att_reason_model = cls.env["hr.attendance.reason"]
        cls.department_model = cls.env["hr.department"]
        cls.employee_model = cls.env["hr.employee"]

        # Import the controller class
        from odoo.addons.hr_attendance_reason_department.controllers import main

        cls.controller_class = main.HrAttendance

        # Create attendance reasons
        cls.att_reason_in_company = cls.att_reason_model.create(
            {
                "name": "Company Sign-in",
                "code": "CSI",
                "action_type": "sign_in",
                "show_on_attendance_screen": True,
            }
        )
        cls.att_reason_in_dept_1 = cls.att_reason_model.create(
            {
                "name": "Dept1 Sign-in",
                "code": "D1I",
                "action_type": "sign_in",
                "show_on_attendance_screen": True,
            }
        )
        cls.att_reason_in_dept_2 = cls.att_reason_model.create(
            {
                "name": "Dept2 Sign-in",
                "code": "D2I",
                "action_type": "sign_in",
                "show_on_attendance_screen": True,
            }
        )
        cls.att_reason_out_company = cls.att_reason_model.create(
            {
                "name": "Company Sign-out",
                "code": "CSO",
                "action_type": "sign_out",
                "show_on_attendance_screen": True,
            }
        )
        cls.att_reason_out_dept_1 = cls.att_reason_model.create(
            {
                "name": "Dept1 Sign-out",
                "code": "D1O",
                "action_type": "sign_out",
                "show_on_attendance_screen": True,
            }
        )

        # Configure company defaults
        cls.env.company.show_reason_on_attendance_screen = True
        cls.env.company.required_reason_on_attendance_screen = False
        cls.env.company.reason_on_attendance_screen_default_sign_in = (
            cls.att_reason_in_company.id
        )
        cls.env.company.reason_on_attendance_screen_default_sign_out = (
            cls.att_reason_out_company.id
        )

        # Create departments
        cls.department_1 = cls.department_model.create(
            {
                "name": "Department 1",
                "default_sign_in_reason_id": cls.att_reason_in_dept_1.id,
                "default_sign_out_reason_id": cls.att_reason_out_dept_1.id,
            }
        )
        cls.department_2 = cls.department_model.create(
            {
                "name": "Department 2",
                # No department defaults set
            }
        )

        # Create users and employees
        cls.user_1 = new_test_user(
            cls.env,
            login="test-user-1",
            groups="base.group_user,hr_attendance.group_hr_attendance_own_reader",
        )
        cls.employee_1 = cls.employee_model.create(
            {
                "name": "Employee 1",
                "user_id": cls.user_1.id,
                "department_id": cls.department_1.id,
            }
        )

        cls.user_2 = new_test_user(
            cls.env,
            login="test-user-2",
            groups="base.group_user,hr_attendance.group_hr_attendance_own_reader",
        )
        cls.employee_2 = cls.employee_model.create(
            {
                "name": "Employee 2",
                "user_id": cls.user_2.id,
                "department_id": cls.department_2.id,
            }
        )

        cls.user_no_dept = new_test_user(
            cls.env,
            login="test-user-no-dept",
            groups="base.group_user,hr_attendance.group_hr_attendance_own_reader",
        )
        cls.employee_no_dept = cls.employee_model.create(
            {
                "name": "Employee No Department",
                "user_id": cls.user_no_dept.id,
            }
        )

    def _get_settings(self, company, employee=None):
        """Helper method to get attendance reason settings."""
        controller = self.controller_class()
        return controller._get_attendance_reason_settings(company, employee)

    @users("test-user-1")
    def test_ac1_department_default_applies(self):
        """AC1: Department default applies to that department's employees."""
        company = self.env.company
        settings = self._get_settings(company, employee=self.employee_1)

        # Department defaults should be returned
        self.assertEqual(
            settings["default_sign_in_reason_id"],
            self.att_reason_in_dept_1.id,
            "Department 1 default sign-in reason should be used",
        )
        self.assertEqual(
            settings["default_sign_out_reason_id"],
            self.att_reason_out_dept_1.id,
            "Department 1 default sign-out reason should be used",
        )

    def test_ac2_fallback_to_company_default(self):
        """AC2: A department with no default falls back to the company default."""
        company = self.env.company
        settings = self._get_settings(company, employee=self.employee_2)

        # Company defaults should be returned
        self.assertEqual(
            settings["default_sign_in_reason_id"],
            self.att_reason_in_company.id,
            "Company default sign-in reason should be used when department has none",
        )
        self.assertEqual(
            settings["default_sign_out_reason_id"],
            self.att_reason_out_company.id,
            "Company default sign-out reason should be used when department has none",
        )

    def test_ac3_department_isolation(self):
        """AC3: Changing a department default does not affect other departments."""
        company = self.env.company

        # Get settings for employee 1 (has department defaults)
        settings_1 = self._get_settings(company, employee=self.employee_1)

        # Get settings for employee 2 (falls back to company defaults)
        settings_2 = self._get_settings(company, employee=self.employee_2)

        # Default sign-in should differ between employees
        self.assertNotEqual(
            settings_1["default_sign_in_reason_id"],
            settings_2["default_sign_in_reason_id"],
            "Different departments should return different defaults",
        )

        # Now change department 2's default
        self.department_2.default_sign_in_reason_id = self.att_reason_in_dept_2.id

        # Re-check settings
        settings_1_updated = self._get_settings(company, employee=self.employee_1)
        settings_2_updated = self._get_settings(company, employee=self.employee_2)

        # Employee 1 should still have the same default
        self.assertEqual(
            settings_1["default_sign_in_reason_id"],
            settings_1_updated["default_sign_in_reason_id"],
            "Changing department 2 should not affect department 1",
        )

        # Employee 2 should now have the new department 2 default
        self.assertEqual(
            settings_2_updated["default_sign_in_reason_id"],
            self.att_reason_in_dept_2.id,
            "Department 2 should use its updated default",
        )

    def test_employee_without_department_fallback(self):
        """Test that an employee with no department falls back to company defaults."""
        company = self.env.company
        settings = self._get_settings(company, employee=self.employee_no_dept)

        # Company defaults should be returned
        self.assertEqual(
            settings["default_sign_in_reason_id"],
            self.att_reason_in_company.id,
            "Company default should be used when employee has no department",
        )
        self.assertEqual(
            settings["default_sign_out_reason_id"],
            self.att_reason_out_company.id,
            "Company default should be used when employee has no department",
        )

    def test_model_fields_exist(self):
        """Test that the new fields exist on the department model."""
        department = self.department_model.create({"name": "Test Department"})

        # Fields should exist and be writable
        department.default_sign_in_reason_id = self.att_reason_in_dept_1.id
        department.default_sign_out_reason_id = self.att_reason_out_dept_1.id

        self.assertEqual(
            department.default_sign_in_reason_id.id,
            self.att_reason_in_dept_1.id,
        )
        self.assertEqual(
            department.default_sign_out_reason_id.id,
            self.att_reason_out_dept_1.id,
        )
