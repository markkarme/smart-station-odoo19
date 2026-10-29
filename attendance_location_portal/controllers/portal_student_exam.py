import logging
from datetime import timedelta
from urllib.parse import urlencode, quote

from odoo import _, fields, http
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.http import request
from odoo.addons.portal.controllers.portal import pager as portal_pager

from .portal_common import PortalHrMixin

_logger = logging.getLogger(__name__)

EXAM_STATE_LABELS = {
    "draft": "Draft",
    "ongoing": "On Going",
    "close": "Closed",
    "cancel": "Canceled",
}

EXAM_STATE_BADGES = {
    "draft": "text-bg-secondary",
    "ongoing": "text-bg-info",
    "close": "text-bg-success",
    "cancel": "text-bg-danger",
}

DAY_LABELS = {
    "sunday": "Sunday",
    "monday": "Monday",
    "tuesday": "Tuesday",
    "wednesday": "Wednesday",
    "thursday": "Thursday",
    "friday": "Friday",
    "saturday": "Saturday",
}


class PortalStudentExamController(PortalHrMixin, http.Controller):
    def _require_exam_admin(self):
        if not self._is_portal_exam_admin():
            raise AccessError(_("You are not allowed to manage student exams."))

    def _failed_page(self, message):
        return request.render(
            "attendance_location_portal.portal_student_exam_failed_page",
            {
                "page_name": "portal_student_exam_failed",
                "error_message": message,
            },
        )

    def _allowed_companies(self):
        return request.env.user.company_ids.sorted("name")

    def _get_student_exam(self, exam_id):
        self._require_exam_admin()
        exam = request.env["student.exam"].sudo().browse(exam_id)
        company_ids = set(self._portal_user_company_ids())
        if (
            not exam.exists()
            or not exam.company_id
            or exam.company_id.id not in company_ids
        ):
            raise AccessError(_("This exam does not exist or is not accessible."))
        return exam

    def _state_labels(self):
        return {key: request.env._(label) for key, label in EXAM_STATE_LABELS.items()}

    def _day_labels(self):
        return {key: request.env._(label) for key, label in DAY_LABELS.items()}

    def _float_to_time(self, value):
        value = value or 0.0
        hours = int(value)
        minutes = int(round((value - hours) * 60))
        if minutes == 60:
            hours += 1
            minutes = 0
        return "%02d:%02d" % (hours, minutes)

    def _time_to_float(self, value):
        value = (value or "").strip()
        if not value:
            return 0.0
        parts = value.split(":")
        try:
            hours = int(parts[0])
            minutes = int(parts[1]) if len(parts) > 1 else 0
        except (TypeError, ValueError):
            return 0.0
        return hours + (minutes / 60.0)

    def _standards_for_company(self, company):
        return request.env["student.standard"].sudo().search(
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

    def _years(self):
        return request.env["year.year"].sudo().search([], order="name, id")

    def _subjects(self):
        return request.env["student.subject"].sudo().search([], order="name, id")

    def _subjects_for_exam(self, exam):
        """Match backend: mold-allowed subjects when available, else all subjects."""
        if "allowed_subject_ids" in exam._fields and exam.allowed_subject_ids:
            return exam.allowed_subject_ids.sorted(lambda subject: (subject.name or "", subject.id))
        return self._subjects()

    def _build_subject_lines(self, start_date, end_date, time_from, time_to):
        if not start_date or not end_date:
            return []
        start = fields.Date.to_date(start_date)
        end = fields.Date.to_date(end_date)
        if end < start:
            raise UserError(_("Start date must be Greater to end date"))
        lines = []
        exam_date = start
        index = 0
        while exam_date <= end:
            lines.append(
                (
                    0,
                    0,
                    {
                        "sequence": (index + 1) * 10,
                        "date": exam_date,
                        "day": exam_date.strftime("%A").lower(),
                        "time_from": time_from,
                        "time_to": time_to,
                    },
                )
            )
            exam_date = exam_date + timedelta(days=1)
            index += 1
        return lines

    def _load_exam_students(self, exam):
        if not exam.company_id or not exam.standard:
            exam.write({"student_ids": [(5, 0, 0)]})
            return
        students = request.env["res.partner"].sudo().search(
            exam._get_student_domain(),
            order="roll_no, name",
        )
        exam.write({"student_ids": [(6, 0, students.ids)]})

    @http.route(
        ["/my/student_exams", "/my/student_exams/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_student_exams(
        self,
        page=1,
        sortby=None,
        filterby=None,
        search=None,
        search_in="all",
        **kwargs,
    ):
        try:
            self._require_exam_admin()
        except AccessError as error:
            return self._failed_page(str(error))

        companies = self._allowed_companies()
        exam_model = request.env["student.exam"].sudo()
        domain = self._portal_company_domain()

        searchbar_filters = self._portal_company_searchbar_filters(
            companies,
            base={
                "all": {"label": _("All"), "domain": [], "sequence": 10},
                "draft": {
                    "label": _("Draft"),
                    "domain": [("state", "=", "draft")],
                    "sequence": 20,
                },
                "ongoing": {
                    "label": _("On Going"),
                    "domain": [("state", "=", "ongoing")],
                    "sequence": 30,
                },
                "close": {
                    "label": _("Closed"),
                    "domain": [("state", "=", "close")],
                    "sequence": 40,
                },
                "cancel": {
                    "label": _("Canceled"),
                    "domain": [("state", "=", "cancel")],
                    "sequence": 50,
                },
            },
        )
        search_inputs = self._portal_student_searchbar_inputs(
            name_fields=["student_ids.name"],
            id_fields=["student_ids.stud_id"],
            extra_all_domains=lambda value: [
                [("name", "ilike", value)],
                [("standard.name", "ilike", value)],
                [("division.name", "ilike", value)],
                [("class_id.name", "ilike", value)],
            ],
            extra_inputs={
                "exam": {
                    "input": "exam",
                    "label": _("Search in Exam"),
                    "sequence": 40,
                    "domain": lambda value: [("name", "ilike", value)],
                },
            },
        )
        searchbar_sortings = {
            "date": {"label": _("Newest"), "order": "start_date desc, id desc"},
            "name": {"label": _("Exam"), "order": "name, id desc"},
            "state": {"label": _("Status"), "order": "state, start_date desc"},
        }
        searchbar = self._portal_apply_searchbar(
            domain,
            searchbar_filters=searchbar_filters,
            searchbar_inputs=search_inputs,
            searchbar_sortings=searchbar_sortings,
            filterby=filterby,
            search=search,
            search_in=search_in,
            sortby=sortby,
            default_filterby="all",
            default_search_in="all",
            default_sortby="date",
        )
        domain = searchbar["domain"]
        exam_count = exam_model.search_count(domain)
        pager = portal_pager(
            url="/my/student_exams",
            url_args={
                "sortby": searchbar["sortby"],
                "filterby": searchbar["filterby"],
                "search": searchbar["search"],
                "search_in": searchbar["search_in"],
            },
            total=exam_count,
            page=page,
            step=self._items_per_page,
        )
        exams = exam_model.search(
            domain,
            order=searchbar["order"],
            limit=self._items_per_page,
            offset=pager["offset"],
        )
        return request.render(
            "attendance_location_portal.portal_my_student_exams",
            {
                "page_name": "portal_student_exams",
                "exams": exams,
                "pager": pager,
                "show_company": len(companies) > 1,
                "state_labels": self._state_labels(),
                "state_badges": EXAM_STATE_BADGES,
                "default_url": "/my/student_exams",
                "searchbar_filters": searchbar["searchbar_filters"],
                "filterby": searchbar["filterby"],
                "searchbar_inputs": searchbar["searchbar_inputs"],
                "search_in": searchbar["search_in"],
                "search": searchbar["search"],
                "searchbar_sortings": searchbar["searchbar_sortings"],
                "sortby": searchbar["sortby"],
            },
        )

    @http.route("/my/student_exams/new", type="http", auth="user", website=True)
    def portal_student_exam_new(self, **kwargs):
        try:
            self._require_exam_admin()
        except AccessError as error:
            return self._failed_page(str(error))

        companies = self._allowed_companies()
        if not companies:
            return self._failed_page(_("No allowed companies are configured for your user."))

        try:
            company_id = int(kwargs.get("company_id") or companies[:1].id)
        except (TypeError, ValueError):
            company_id = companies[:1].id
        company = companies.filtered(lambda item: item.id == company_id)[:1]
        if not company:
            return self._failed_page(_("This company is not in your allowed companies."))

        try:
            standard_id = int(kwargs.get("standard_id") or 0) or False
        except (TypeError, ValueError):
            standard_id = False
        standards = self._standards_for_company(company)
        standard = standards.filtered(lambda item: item.id == standard_id)[:1]
        divisions = self._divisions_for_standard(standard)

        return request.render(
            "attendance_location_portal.portal_student_exam_new",
            {
                "page_name": "portal_student_exam_new",
                "companies": companies,
                "company": company,
                "standards": standards,
                "standard": standard,
                "divisions": divisions,
                "classes": self._classes(),
                "years": self._years(),
                "name": kwargs.get("name") or "",
                "start_date": kwargs.get("start_date") or "",
                "end_date": kwargs.get("end_date") or "",
                "time_from": kwargs.get("time_from") or "08:00",
                "time_to": kwargs.get("time_to") or "10:00",
                "division_id": kwargs.get("division_id") or "",
                "class_id": kwargs.get("class_id") or "",
                "curr_year": kwargs.get("curr_year") or "",
                "error_message": kwargs.get("error"),
            },
        )

    @http.route(
        "/my/student_exams/submit",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_student_exam_submit(self, **post):
        try:
            self._require_exam_admin()
        except AccessError as error:
            return self._failed_page(str(error))

        companies = self._allowed_companies()
        try:
            company_id = int(post.get("company_id") or 0)
            standard_id = int(post.get("standard_id") or 0)
            division_id = int(post.get("division_id") or 0) or False
            class_id = int(post.get("class_id") or 0) or False
            curr_year = int(post.get("curr_year") or 0) or False
        except (TypeError, ValueError):
            return request.redirect(
                "/my/student_exams/new?%s"
                % urlencode({"error": _("Invalid exam values.")})
            )

        company = companies.filtered(lambda item: item.id == company_id)[:1]
        if not company:
            return self._failed_page(_("This company is not in your allowed companies."))

        standards = self._standards_for_company(company)
        standard = standards.filtered(lambda item: item.id == standard_id)[:1]
        if not standard:
            return request.redirect(
                "/my/student_exams/new?%s"
                % urlencode(
                    {
                        "company_id": company.id,
                        "error": _("Please select a valid standard."),
                    }
                )
            )

        name = (post.get("name") or "").strip()
        start_date = post.get("start_date")
        end_date = post.get("end_date")
        time_from = self._time_to_float(post.get("time_from"))
        time_to = self._time_to_float(post.get("time_to"))
        if not name or not start_date or not end_date:
            return request.redirect(
                "/my/student_exams/new?%s"
                % urlencode(
                    {
                        "company_id": company.id,
                        "standard_id": standard.id,
                        "error": _("Name, start date and end date are required."),
                    }
                )
            )

        try:
            subject_lines = self._build_subject_lines(
                start_date, end_date, time_from, time_to
            )
            exam = request.env["student.exam"].sudo().create(
                {
                    "name": name,
                    "company_id": company.id,
                    "standard": standard.id,
                    "division": division_id,
                    "class_id": class_id,
                    "curr_year": curr_year,
                    "start_date": start_date,
                    "end_date": end_date,
                    "time_from": time_from,
                    "time_to": time_to,
                    "subject_line": subject_lines,
                }
            )
            self._load_exam_students(exam)
        except (UserError, ValidationError) as error:
            return request.redirect(
                "/my/student_exams/new?%s"
                % urlencode(
                    {
                        "company_id": company.id,
                        "standard_id": standard.id,
                        "division_id": division_id or "",
                        "class_id": class_id or "",
                        "curr_year": curr_year or "",
                        "name": name,
                        "start_date": start_date,
                        "end_date": end_date,
                        "time_from": post.get("time_from") or "",
                        "time_to": post.get("time_to") or "",
                        "error": str(error),
                    }
                )
            )
        except Exception as error:
            _logger.exception("Portal student exam create failed: %s", error)
            return self._failed_page(_("Could not create the exam."))

        return request.redirect("/my/student_exams/%s" % exam.id)

    @http.route(
        "/my/student_exams/<int:exam_id>",
        type="http",
        auth="user",
        website=True,
    )
    def portal_student_exam_detail(self, exam_id, **kwargs):
        try:
            exam = self._get_student_exam(exam_id)
        except AccessError as error:
            return self._failed_page(str(error))

        return request.render(
            "attendance_location_portal.portal_student_exam_detail",
            {
                "page_name": "portal_student_exam_detail",
                "exam": exam,
                "subjects": self._subjects_for_exam(exam),
                "state_labels": self._state_labels(),
                "state_badges": EXAM_STATE_BADGES,
                "day_labels": self._day_labels(),
                "float_to_time": self._float_to_time,
                "is_exam_editable": exam.state == "draft",
                "message": kwargs.get("message"),
                "error_message": kwargs.get("error"),
            },
        )

    @http.route(
        "/my/student_exams/<int:exam_id>/subjects",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_student_exam_subjects(self, exam_id, **post):
        try:
            exam = self._get_student_exam(exam_id)
        except AccessError as error:
            return self._failed_page(str(error))
        if exam.state != "draft":
            return request.redirect(
                "/my/student_exams/%s?%s"
                % (exam.id, urlencode({"error": _("Only draft exams can be edited.")}))
            )

        line_ids = request.httprequest.form.getlist("line_id")
        subject_ids = request.httprequest.form.getlist("subject_id")
        dates = request.httprequest.form.getlist("date")
        times_from = request.httprequest.form.getlist("time_from")
        times_to = request.httprequest.form.getlist("time_to")
        delete_line_ids = set()
        for raw_id in request.httprequest.form.getlist("delete_line_ids"):
            try:
                delete_line_ids.add(int(raw_id))
            except (TypeError, ValueError):
                continue

        try:
            allowed_subjects = self._subjects_for_exam(exam)
            allowed_ids = set(allowed_subjects.ids)
            commands = []
            kept_ids = set()
            for index, line_id in enumerate(line_ids):
                try:
                    line_id = int(line_id)
                    subject_id = int(subject_ids[index] or 0) or False
                except (TypeError, ValueError, IndexError):
                    continue
                if line_id and line_id in delete_line_ids:
                    commands.append((2, line_id))
                    continue
                if subject_id and allowed_ids and subject_id not in allowed_ids:
                    raise UserError(
                        _("Subject is not allowed for this exam standard/division.")
                    )
                date_value = dates[index] if index < len(dates) else False
                time_from = self._time_to_float(
                    times_from[index] if index < len(times_from) else ""
                )
                time_to = self._time_to_float(
                    times_to[index] if index < len(times_to) else ""
                )
                day = (
                    fields.Date.to_date(date_value).strftime("%A").lower()
                    if date_value
                    else False
                )
                vals = {
                    "subject_id": subject_id,
                    "date": date_value or False,
                    "day": day,
                    "time_from": time_from,
                    "time_to": time_to,
                }
                if line_id:
                    commands.append((1, line_id, vals))
                    kept_ids.add(line_id)
                else:
                    commands.append((0, 0, vals))
            for line in exam.subject_line:
                if line.id not in kept_ids and line.id not in delete_line_ids:
                    # Keep lines that were not posted only if still present;
                    # posted rows already covered above.
                    pass
            exam.write({"subject_line": commands})
            params = {"message": _("Subjects updated.")}
        except (UserError, ValidationError) as error:
            params = {"error": str(error)}
        except Exception as error:
            _logger.exception("Portal student exam subjects update failed: %s", error)
            params = {"error": _("Could not update subjects.")}
        return request.redirect("/my/student_exams/%s?%s" % (exam.id, urlencode(params)))

    @http.route(
        "/my/student_exams/<int:exam_id>/action",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_student_exam_action(self, exam_id, **post):
        try:
            exam = self._get_student_exam(exam_id)
        except AccessError as error:
            return self._failed_page(str(error))

        action = (post.get("exam_action") or "").strip()
        params = {}
        try:
            if action == "confirm" and exam.state == "draft":
                exam.ongoing_exam()
                params["message"] = _("Exam confirmed.")
            elif action == "cancel" and exam.state == "draft":
                exam.cancel_exam()
                params["message"] = _("Exam canceled.")
            elif action == "complete" and exam.state == "ongoing":
                exam.close_exam()
                params["message"] = _("Exam completed.")
            elif action == "reload_students" and exam.state == "draft":
                self._load_exam_students(exam)
                params["message"] = _("Students reloaded.")
            elif action == "add_subject_line" and exam.state == "draft":
                day = False
                if exam.start_date:
                    day = exam.start_date.strftime("%A").lower()
                exam.write(
                    {
                        "subject_line": [
                            (
                                0,
                                0,
                                {
                                    "date": exam.start_date,
                                    "day": day,
                                    "time_from": exam.time_from,
                                    "time_to": exam.time_to,
                                },
                            )
                        ]
                    }
                )
                params["message"] = _("Subject line added.")
            elif action == "delete":
                exam.unlink()
                return request.redirect("/my/student_exams")
            else:
                params["error"] = _("This action is not available.")
        except (UserError, ValidationError) as error:
            params["error"] = str(error)
        except Exception as error:
            _logger.exception("Portal student exam action failed: %s", error)
            params["error"] = _("Could not update the exam.")
        return request.redirect("/my/student_exams/%s?%s" % (exam.id, urlencode(params)))

    @http.route(
        "/my/student_exams/<int:exam_id>/schedule",
        type="http",
        auth="user",
        website=True,
    )
    def portal_student_exam_schedule(self, exam_id, **kwargs):
        try:
            exam = self._get_student_exam(exam_id)
        except AccessError:
            return request.not_found()

        report = request.env.ref("jt_education_exam.action_report_exam_schedule")
        lang = request.env.lang if (request.env.lang or "").startswith("ar") else "ar_001"
        pdf_content, _report_type = (
            request.env["ir.actions.report"]
            .sudo()
            .with_context(lang=lang)
            ._render_qweb_pdf(report, exam.id)
        )
        filename = (exam.name or _("Exam Schedule")).replace('"', "")
        return request.make_response(
            pdf_content,
            headers=[
                ("Content-Type", "application/pdf"),
                ("Content-Length", len(pdf_content)),
                (
                    "Content-Disposition",
                    "inline; filename*=UTF-8''%s.pdf" % quote(filename),
                ),
            ],
        )
