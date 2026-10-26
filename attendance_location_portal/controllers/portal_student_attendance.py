import logging
from urllib.parse import urlencode

from odoo import _, fields, http
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.http import request
from odoo.addons.portal.controllers.portal import pager as portal_pager

from .portal_common import PortalHrMixin

_logger = logging.getLogger(__name__)

ATTENDANCE_STATUS_ACTIONS = {
    "present": "present_student",
    "absence_reason": "absence_reason_student",
    "absence_noreason": "absence_noreason_student",
    "late": "late_student",
    "withdraw": "withdraw_student",
}

ATTENDANCE_STATUS_LABELS = {
    "present": "Present",
    "absence_reason": "Absent with Reason",
    "absence_noreason": "Absent with no Reason",
    "late": "Late",
    "withdraw": "Withdraw",
    "none": "Not set",
}

ATTENDANCE_STATUS_BADGES = {
    "present": "text-bg-success",
    "absence_reason": "text-bg-warning",
    "absence_noreason": "text-bg-danger",
    "late": "text-bg-info",
    "withdraw": "text-bg-secondary",
    "none": "text-bg-light",
}


class PortalStudentAttendanceController(PortalHrMixin, http.Controller):
    def _require_attendance_admin(self):
        if not self._is_portal_attendance_admin():
            raise AccessError(_("You are not allowed to manage student attendance."))

    def _student_attendance_domain(self):
        return self._portal_company_domain()

    def _get_student_attendance(self, attendance_id):
        self._require_attendance_admin()
        attendance = request.env["attendance.attendance"].sudo().browse(attendance_id)
        company_ids = set(self._portal_user_company_ids())
        if (
            not attendance.exists()
            or not attendance.company_id
            or attendance.company_id.id not in company_ids
        ):
            raise AccessError(_("This attendance does not exist or is not accessible."))
        return attendance

    def _failed_page(self, message):
        return request.render(
            "attendance_location_portal.portal_student_attendance_failed_page",
            {
                "page_name": "portal_student_attendance_failed",
                "error_message": message,
            },
        )

    def _status_labels(self):
        return {
            key: request.env._(label)
            for key, label in ATTENDANCE_STATUS_LABELS.items()
        }

    def _allowed_companies(self):
        return request.env.user.company_ids.sorted("name")

    def _standards_for_company(self, company):
        Standard = request.env["student.standard"].sudo()
        return Standard.search(
            [
                "|",
                ("company_ids", "=", False),
                ("company_ids", "in", [company.id]),
            ],
            order="name, id",
        )

    def _divisions_for_standard(self, standard):
        Division = request.env["standard.division"].sudo()
        if not standard:
            return Division.browse()
        return Division.search(
            [("standard_id", "in", [False, standard.id])],
            order="name, id",
        )

    def _classes(self):
        return request.env["student.class"].sudo().search([], order="name, id")

    def _subjects(self):
        return request.env["student.subject"].sudo().search([], order="name, id")

    @http.route(
        ["/my/student_attendances", "/my/student_attendances/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_student_attendances(self, page=1, **kwargs):
        try:
            self._require_attendance_admin()
        except AccessError as error:
            return self._failed_page(str(error))

        attendance_model = request.env["attendance.attendance"].sudo()
        domain = self._student_attendance_domain()
        attendance_count = attendance_model.search_count(domain)
        pager = portal_pager(
            url="/my/student_attendances",
            total=attendance_count,
            page=page,
            step=self._items_per_page,
        )
        attendances = attendance_model.search(
            domain,
            order="date desc, id desc",
            limit=self._items_per_page,
            offset=pager["offset"],
        )
        return request.render(
            "attendance_location_portal.portal_my_student_attendances",
            {
                "page_name": "portal_student_attendances",
                "attendances": attendances,
                "pager": pager,
                "show_company": len(self._allowed_companies()) > 1,
            },
        )

    @http.route("/my/student_attendances/new", type="http", auth="user", website=True)
    def portal_student_attendance_new(self, **kwargs):
        try:
            self._require_attendance_admin()
        except AccessError as error:
            return self._failed_page(str(error))

        companies = self._allowed_companies()
        if not companies:
            return self._failed_page(_("No allowed companies are configured for your user."))

        company_id = kwargs.get("company_id")
        try:
            company_id = int(company_id) if company_id else companies[:1].id
        except (TypeError, ValueError):
            company_id = companies[:1].id
        company = companies.filtered(lambda company: company.id == company_id)[:1]
        if not company:
            return self._failed_page(_("This company is not in your allowed companies."))

        standard_id = kwargs.get("standard_id")
        try:
            standard_id = int(standard_id) if standard_id else False
        except (TypeError, ValueError):
            standard_id = False
        standards = self._standards_for_company(company)
        standard = standards.filtered(lambda item: item.id == standard_id)[:1]

        division_id = kwargs.get("division_id")
        try:
            division_id = int(division_id) if division_id else False
        except (TypeError, ValueError):
            division_id = False
        divisions = self._divisions_for_standard(standard)
        division = divisions.filtered(lambda item: item.id == division_id)[:1]

        class_id = kwargs.get("class_id")
        try:
            class_id = int(class_id) if class_id else False
        except (TypeError, ValueError):
            class_id = False

        return request.render(
            "attendance_location_portal.portal_student_attendance_new",
            {
                "page_name": "portal_student_attendance_new",
                "companies": companies,
                "company": company,
                "standards": standards,
                "standard": standard,
                "divisions": divisions,
                "division": division,
                "classes": self._classes(),
                "class_id": class_id,
                "subjects": self._subjects(),
                "date": kwargs.get("date") or fields.Date.context_today(request.env.user),
                "error_message": kwargs.get("error"),
            },
        )

    @http.route(
        "/my/student_attendances/submit",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_student_attendance_submit(self, **post):
        try:
            self._require_attendance_admin()
        except AccessError as error:
            return self._failed_page(str(error))

        companies = self._allowed_companies()
        try:
            company_id = int(post.get("company_id") or 0)
            standard_id = int(post.get("standard_id") or 0)
            division_id = int(post.get("division_id") or 0)
            class_id = int(post.get("class_id") or 0) or False
        except (TypeError, ValueError):
            return request.redirect(
                "/my/student_attendances/new?%s"
                % urlencode({"error": _("Invalid attendance values.")})
            )

        company = companies.filtered(lambda item: item.id == company_id)[:1]
        if not company:
            return self._failed_page(_("This company is not in your allowed companies."))

        standards = self._standards_for_company(company)
        standard = standards.filtered(lambda item: item.id == standard_id)[:1]
        if not standard:
            return request.redirect(
                "/my/student_attendances/new?%s"
                % urlencode(
                    {
                        "company_id": company.id,
                        "error": _("Please select a valid standard."),
                    }
                )
            )

        divisions = self._divisions_for_standard(standard)
        division = divisions.filtered(lambda item: item.id == division_id)[:1]
        if not division:
            return request.redirect(
                "/my/student_attendances/new?%s"
                % urlencode(
                    {
                        "company_id": company.id,
                        "standard_id": standard.id,
                        "error": _("Please select a valid division."),
                    }
                )
            )

        student_class = request.env["student.class"].sudo().browse(class_id) if class_id else False
        if class_id and not student_class.exists():
            student_class = False

        subject_ids = request.httprequest.form.getlist("subject_id")
        try:
            subject_ids = [int(subject_id) for subject_id in subject_ids if subject_id]
        except (TypeError, ValueError):
            subject_ids = []

        date_value = post.get("date") or fields.Date.context_today(request.env.user)
        try:
            attendance = request.env["attendance.attendance"].sudo().create(
                {
                    "company_id": company.id,
                    "standard_id": standard.id,
                    "division_id": division.id,
                    "class_id": student_class.id if student_class else False,
                    "date": date_value,
                    "subject_id": [(6, 0, subject_ids)],
                }
            )
            students = request.env["res.partner"].sudo().search(
                attendance._get_student_domain()
            )
            attendance.write(
                {
                    "attendance_ids": [
                        (0, 0, {"student_id": student.id}) for student in students
                    ]
                }
            )
        except (UserError, ValidationError) as error:
            return request.redirect(
                "/my/student_attendances/new?%s"
                % urlencode(
                    {
                        "company_id": company.id,
                        "standard_id": standard.id,
                        "division_id": division.id,
                        "class_id": class_id or "",
                        "date": date_value,
                        "error": str(error),
                    }
                )
            )
        except Exception as error:
            _logger.exception("Portal student attendance create failed: %s", error)
            return self._failed_page(_("Could not create the attendance record."))

        return request.redirect("/my/student_attendances/%s" % attendance.id)

    @http.route(
        "/my/student_attendances/<int:attendance_id>",
        type="http",
        auth="user",
        website=True,
    )
    def portal_student_attendance_detail(self, attendance_id, **kwargs):
        try:
            attendance = self._get_student_attendance(attendance_id)
        except AccessError as error:
            return self._failed_page(str(error))

        return request.render(
            "attendance_location_portal.portal_student_attendance_detail",
            {
                "page_name": "portal_student_attendance_detail",
                "attendance": attendance,
                "status_labels": self._status_labels(),
                "status_badges": ATTENDANCE_STATUS_BADGES,
                "message": kwargs.get("message"),
                "error_message": kwargs.get("error"),
            },
        )

    @http.route(
        "/my/student_attendances/<int:attendance_id>/action",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_student_attendance_action(self, attendance_id, **post):
        try:
            attendance = self._get_student_attendance(attendance_id)
        except AccessError as error:
            return self._failed_page(str(error))

        action = (post.get("attendance_action") or "").strip()
        line_ids = request.httprequest.form.getlist("line_ids")
        try:
            line_ids = [int(line_id) for line_id in line_ids if line_id]
        except (TypeError, ValueError):
            line_ids = []

        lines = attendance.attendance_ids.filtered(lambda line: line.id in line_ids)
        params = {}
        try:
            if action == "select_all":
                attendance.select_all_line()
                params["message"] = _("Selection updated.")
            elif action in ATTENDANCE_STATUS_ACTIONS:
                if not lines:
                    params["error"] = _("Please select at least one student.")
                else:
                    attendance.attendance_ids.write({"selected": False})
                    lines.write({"selected": True})
                    getattr(attendance, ATTENDANCE_STATUS_ACTIONS[action])()
                    params["message"] = _("Attendance updated.")
            else:
                params["error"] = _("Unknown attendance action.")
        except (UserError, ValidationError) as error:
            params["error"] = str(error)
        except Exception as error:
            _logger.exception("Portal student attendance action failed: %s", error)
            params["error"] = _("Could not update attendance.")

        return request.redirect(
            "/my/student_attendances/%s?%s" % (attendance.id, urlencode(params))
        )
