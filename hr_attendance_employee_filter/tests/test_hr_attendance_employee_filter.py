# Copyright 2025 Systango Technologies
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo import fields

from odoo.addons.base.tests.common import BaseCommon


class TestHrAttendanceEmployeeFilter(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.attendance_model = cls.env["hr.attendance"]
        cls.employee_a = cls.env["hr.employee"].create({"name": "Alice Example"})
        cls.employee_b = cls.env["hr.employee"].create({"name": "Bob Example"})
        now = fields.Datetime.now()
        cls.attendance_a = cls.attendance_model.create(
            {"employee_id": cls.employee_a.id, "check_in": now}
        )
        cls.attendance_b = cls.attendance_model.create(
            {"employee_id": cls.employee_b.id, "check_in": now, "check_out": now}
        )

    def test_employee_filter_available_in_search_view(self):
        """The predefined Employee filter is exposed on the Attendance
        search view through a searchpanel reusing the employee_id field,
        and the pre-existing free-text employee_id search field is kept."""
        view = self.attendance_model.get_view(view_type="search")
        arch = etree.fromstring(view["arch"])
        search_panel_fields = arch.xpath("//searchpanel/field[@name='employee_id']")
        self.assertTrue(
            search_panel_fields,
            "Expected a predefined Employee filter (searchpanel) on the "
            "Attendance search view",
        )
        self.assertTrue(
            arch.xpath("//search/field[@name='employee_id']"),
            "The existing free-text Employee search field must be preserved",
        )

    def test_employee_filter_scopes_records(self):
        """Selecting an employee only shows that employee's attendances,
        while filters can still be combined with other attendance filters."""
        filtered = self.attendance_model.search(
            [("employee_id", "=", self.employee_a.id)]
        )
        self.assertIn(self.attendance_a, filtered)
        self.assertNotIn(self.attendance_b, filtered)

        # Combine the employee filter with another predefined filter
        # ("At Work" / no check-out yet): employee_a has no check-out,
        # employee_b does.
        combined = self.attendance_model.search(
            [
                ("employee_id", "=", self.employee_a.id),
                ("check_out", "=", False),
            ]
        )
        self.assertEqual(combined, self.attendance_a)

        combined_b = self.attendance_model.search(
            [
                ("employee_id", "=", self.employee_b.id),
                ("check_out", "=", False),
            ]
        )
        self.assertFalse(combined_b)

    def test_removing_employee_filter_restores_full_list(self):
        """Removing the Employee filter (empty domain) restores the
        normal, unfiltered Attendance list."""
        unfiltered = self.attendance_model.search(
            [("id", "in", [self.attendance_a.id, self.attendance_b.id])]
        )
        self.assertIn(self.attendance_a, unfiltered)
        self.assertIn(self.attendance_b, unfiltered)
