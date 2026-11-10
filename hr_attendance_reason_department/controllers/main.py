# Copyright 2024 Systango Technologies Pvt. Ltd.
# License LGPL-3 - See http://www.gnu.org/licenses/lgpl-3.0.html

from odoo import http

from odoo.addons.hr_attendance_reason.controllers.main import HrAttendance


class HrAttendance(HrAttendance):
    def _get_attendance_reason_settings(self, company, employee=None):
        """
        Get attendance reason settings, checking department defaults first.
        :param company: The company record
        :param employee: Optional employee record to check department defaults
        :return: Dictionary with reason settings
        """
        show_reason = company.show_reason_on_attendance_screen
        required_reason = company.required_reason_on_attendance_screen

        # Get company defaults
        default_sign_in_reason_id = (
            company.reason_on_attendance_screen_default_sign_in.id
        )
        default_sign_out_reason_id = (
            company.reason_on_attendance_screen_default_sign_out.id
        )

        # Check for department defaults if employee is provided
        if employee and employee.department_id:
            department = employee.department_id
            # Use department defaults if set, otherwise fall back to company
            if department.default_sign_in_reason_id:
                default_sign_in_reason_id = department.default_sign_in_reason_id.id
            if department.default_sign_out_reason_id:
                default_sign_out_reason_id = department.default_sign_out_reason_id.id

        return {
            "show_reason_on_attendance_screen": show_reason,
            "required_reason_on_attendance_screen": required_reason,
            "default_sign_in_reason_id": default_sign_in_reason_id,
            "default_sign_out_reason_id": default_sign_out_reason_id,
        }

    # Override existing methods to pass employee to _get_attendance_reason_settings
    @http.route("/hr_attendance_reason/get_reasons", type="json", auth="public")
    def attendance_get_reasons(self, token, employee_id, pin_code):
        company = self._get_company(token)
        if company:
            employee = http.request.env["hr.employee"].sudo().browse(employee_id)
            if employee.company_id == company and (
                (not company.attendance_kiosk_use_pin) or (employee.pin == pin_code)
            ):
                res = self._get_employee_info_response(employee)
                action_type = (
                    "sign_out"
                    if res.get("attendance_state") == "checked_in"
                    else "sign_in"
                )
                res.update(
                    {
                        "reasons": self._get_attendance_reasons(action_type, company),
                        **self._get_attendance_reason_settings(company, employee),
                    }
                )
                return res
        return {}

    @http.route("/hr_attendance_reason/reason_settings", type="json", auth="public")
    def kiosk_reason_settings(self, token):
        company = self._get_company(token)
        if company:
            # kiosk_reason_settings is called without employee context,
            # so we only return company defaults
            return self._get_attendance_reason_settings(company)
        return {}

    def user_attendance_data(self):
        response = super().user_attendance_data()
        # get the employee
        employee = http.request.env.user.employee_id
        company = employee.company_id if employee else http.request.company
        response.update(self._get_attendance_reason_settings(company, employee))
        # get available reasons for employee company
        reasons = []
        if response.get("attendance_state", False):
            if response.get("attendance_state", False) == "checked_out":
                action_type = "sign_in"
            else:
                action_type = "sign_out"
            reasons = self._get_attendance_reasons(action_type, company)
        response.update({"reasons": reasons})
        return response
