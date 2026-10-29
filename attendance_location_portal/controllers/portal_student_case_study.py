import logging
from urllib.parse import urlencode

from odoo import _, fields, http
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.http import content_disposition, request
from odoo.addons.portal.controllers.portal import pager as portal_pager

from .portal_common import PortalHrMixin

_logger = logging.getLogger(__name__)

CASE_CHAR_FIELDS = [
    "name",
    "nationality",
    "residence",
    "live_with",
    "sibling_order",
]
CASE_TEXT_FIELDS = [
    "referral_reason",
    "birth_health_problems",
    "childhood_illnesses",
    "family_economic_at_birth",
    "family_relationships_general",
    "relation_mother",
    "relation_father",
    "relation_siblings",
    "violence_description",
    "current_health_disease",
    "psychological_complaint",
    "receiving_treatment",
    "hereditary_diseases",
    "do_you_work",
    "practice_sport",
    "artistic_activities",
    "any_skill",
    "routine_habit",
    "school_absence_period",
    "life_changes_symptoms",
    "worst_period",
    "self_harm_history",
    "harm_others_history",
    "substance_medication_history",
    "future_plans",
    "general_appearance",
    "movement_activity_level",
    "thought_coherence",
    "mood_emotional_state",
    "involuntary_movements",
    "physical_injuries",
    "behavioral_notes",
    "depression_anxiety_indicators",
    "initial_diagnosis",
    "therapeutic_goals",
    "treatment_plan",
    "recommendations",
]
CASE_SELECTION_FIELDS = [
    "gender",
    "marital_status",
    "has_siblings",
    "grew_up_with",
    "visited_psychiatrist",
    "smile_type",
    "sitting_posture",
    "eye_contact",
    "voice_tone",
]
CASE_BOOL_FIELDS = [
    "violence_emotional",
    "violence_physical",
    "violence_sexual",
    "violence_neglect",
    "symptom_nervousness",
    "symptom_anxiety",
    "symptom_decreased_interest",
    "symptom_lack_energy",
    "symptom_appetite",
    "symptom_weight",
    "symptom_sleep",
    "symptom_thoughts",
    "symptom_concentration",
    "symptom_memory",
    "symptom_motor",
    "symptom_depressive",
    "symptom_isolation",
    "symptom_worthlessness",
]
CASE_DATE_FIELDS = ["date", "birthdate"]
CASE_INT_FIELDS = ["siblings_count"]


class PortalStudentCaseStudyController(PortalHrMixin, http.Controller):
    def _require_misconduct_admin(self):
        if not self._is_portal_misconduct_admin():
            raise AccessError(_("You are not allowed to manage student misconduct."))

    def _failed_page(self, message):
        return request.render(
            "attendance_location_portal.portal_student_misconduct_failed_page",
            {
                "page_name": "portal_student_misconduct_failed",
                "error_message": message,
            },
        )

    def _allowed_companies(self):
        return request.env.user.company_ids.sorted("name")

    def _students_for_company(self, company):
        Partner = request.env["res.partner"].sudo()
        domain = [("is_student", "=", True)]
        if company:
            domain.append(("company_id", "in", [False, company.id]))
        return Partner.search(domain, order="name, id", limit=3000)

    def _classes(self):
        return request.env["student.class"].sudo().search([], order="name, id")

    def _divisions(self):
        return request.env["standard.division"].sudo().search([], order="name, id")

    def _selection_options(self, model, field_name):
        field = request.env[model]._fields[field_name]
        return [
            {"value": key, "label": request.env._(label)}
            for key, label in field._description_selection(request.env)
        ]

    def _get_case(self, case_id):
        self._require_misconduct_admin()
        case = request.env["student.case.study"].sudo().browse(case_id)
        company_ids = set(self._portal_user_company_ids())
        if (
            not case.exists()
            or not case.company_id
            or case.company_id.id not in company_ids
        ):
            raise AccessError(_("This case study does not exist or is not accessible."))
        return case

    def _case_form_context(self, **extra):
        Case = request.env["student.case.study"].sudo()
        return {
            "classes": self._classes(),
            "divisions": self._divisions(),
            "gender_options": self._selection_options("student.case.study", "gender"),
            "marital_options": self._selection_options("student.case.study", "marital_status"),
            "siblings_options": self._selection_options("student.case.study", "has_siblings"),
            "grew_up_options": self._selection_options("student.case.study", "grew_up_with"),
            "psychiatrist_options": self._selection_options(
                "student.case.study", "visited_psychiatrist"
            ),
            "smile_options": self._selection_options("student.case.study", "smile_type"),
            "posture_options": self._selection_options("student.case.study", "sitting_posture"),
            "eye_options": self._selection_options("student.case.study", "eye_contact"),
            "voice_options": self._selection_options("student.case.study", "voice_tone"),
            "relation_options": self._selection_options(
                "student.case.study.family", "relation_type"
            ),
            "economic_options": self._selection_options(
                "student.case.study.family", "economic_level"
            ),
            "bool_fields": CASE_BOOL_FIELDS,
            "bool_labels": {
                name: Case._fields[name].string for name in CASE_BOOL_FIELDS
            },
            "field_labels": {
                name: Case._fields[name].string
                for name in (
                    CASE_CHAR_FIELDS
                    + CASE_TEXT_FIELDS
                    + CASE_SELECTION_FIELDS
                    + CASE_DATE_FIELDS
                    + CASE_INT_FIELDS
                    + CASE_BOOL_FIELDS
                )
                if name in Case._fields
            },
            **extra,
        }

    def _vals_from_post(self, post, company_id=None):
        vals = {}
        if company_id:
            vals["company_id"] = company_id
        if post.get("student_id"):
            vals["student_id"] = int(post.get("student_id"))
        if post.get("class_id"):
            vals["class_id"] = int(post.get("class_id"))
        elif "class_id" in post:
            vals["class_id"] = False
        if post.get("div_id"):
            vals["div_id"] = int(post.get("div_id"))
        elif "div_id" in post:
            vals["div_id"] = False
        for name in CASE_CHAR_FIELDS + CASE_TEXT_FIELDS:
            if name in post:
                vals[name] = (post.get(name) or "").strip() or False
        for name in CASE_SELECTION_FIELDS:
            if name in post:
                vals[name] = post.get(name) or False
        for name in CASE_DATE_FIELDS:
            if name in post:
                vals[name] = post.get(name) or False
        for name in CASE_INT_FIELDS:
            if name in post:
                try:
                    vals[name] = int(post.get(name) or 0)
                except (TypeError, ValueError):
                    vals[name] = 0
        for name in CASE_BOOL_FIELDS:
            vals[name] = post.get(name) == "1"
        return vals

    def _family_commands_from_post(self, post, existing=None):
        existing = existing or request.env["student.case.study.family"]
        keep_ids = set()
        commands = []
        raw_ids = request.httprequest.form.getlist("family_row_id")
        relations = request.httprequest.form.getlist("family_relation_type")
        names = request.httprequest.form.getlist("family_name")
        ages = request.httprequest.form.getlist("family_age")
        educations = request.httprequest.form.getlist("family_education")
        jobs = request.httprequest.form.getlist("family_job")
        economics = request.httprequest.form.getlist("family_economic_level")
        count = max(len(relations), len(names), len(raw_ids), 0)
        for idx in range(count):
            relation = (relations[idx] if idx < len(relations) else "") or False
            name = (names[idx] if idx < len(names) else "") or False
            education = (educations[idx] if idx < len(educations) else "") or False
            job = (jobs[idx] if idx < len(jobs) else "") or False
            economic = (economics[idx] if idx < len(economics) else "") or False
            try:
                age = int(ages[idx] or 0) if idx < len(ages) else 0
            except (TypeError, ValueError):
                age = 0
            try:
                line_id = int(raw_ids[idx] or 0) if idx < len(raw_ids) else 0
            except (TypeError, ValueError):
                line_id = 0
            if not relation and not name and not education and not job and not age:
                continue
            line_vals = {
                "relation_type": relation or "other",
                "name": name,
                "age": age,
                "education": education,
                "job": job,
                "economic_level": economic,
                "sequence": (idx + 1) * 10,
            }
            if line_id and line_id in existing.ids:
                commands.append((1, line_id, line_vals))
                keep_ids.add(line_id)
            else:
                commands.append((0, 0, line_vals))
        for line in existing:
            if line.id not in keep_ids:
                commands.append((2, line.id))
        return commands

    @http.route(
        ["/my/case_studies", "/my/case_studies/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_case_studies(
        self,
        page=1,
        sortby=None,
        filterby=None,
        search=None,
        search_in="all",
        **kwargs,
    ):
        try:
            self._require_misconduct_admin()
        except AccessError as error:
            return self._failed_page(str(error))

        companies = self._allowed_companies()
        Case = request.env["student.case.study"].sudo()
        domain = self._portal_company_domain()
        searchbar_filters = self._portal_company_searchbar_filters(
            companies,
            base={"all": {"label": _("All"), "domain": [], "sequence": 10}},
        )
        search_inputs = self._portal_student_searchbar_inputs(
            name_fields=["student_id.name", "name"],
            id_fields=["student_id.stud_id", "stud_id"],
            extra_all_domains=lambda value: [
                [("referral_reason", "ilike", value)],
                [("psychologist_id.name", "ilike", value)],
            ],
        )
        searchbar_sortings = {
            "date": {"label": _("Newest"), "order": "date desc, id desc"},
            "student": {"label": _("Student"), "order": "student_id, date desc"},
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
        total = Case.search_count(domain)
        pager = portal_pager(
            url="/my/case_studies",
            url_args={
                "sortby": searchbar["sortby"],
                "filterby": searchbar["filterby"],
                "search": searchbar["search"],
                "search_in": searchbar["search_in"],
            },
            total=total,
            page=page,
            step=self._items_per_page,
        )
        records = Case.search(
            domain,
            order=searchbar["order"],
            limit=self._items_per_page,
            offset=pager["offset"],
        )
        return request.render(
            "attendance_location_portal.portal_my_case_studies",
            {
                "page_name": "portal_case_studies",
                "cases": records,
                "pager": pager,
                "show_company": len(companies) > 1,
                "default_url": "/my/case_studies",
                "searchbar_filters": searchbar["searchbar_filters"],
                "filterby": searchbar["filterby"],
                "searchbar_inputs": searchbar["searchbar_inputs"],
                "search_in": searchbar["search_in"],
                "search": searchbar["search"],
                "searchbar_sortings": searchbar["searchbar_sortings"],
                "sortby": searchbar["sortby"],
                "message": kwargs.get("message"),
                "error_message": kwargs.get("error"),
            },
        )

    @http.route("/my/case_studies/new", type="http", auth="user", website=True)
    def portal_case_study_new(self, **kwargs):
        try:
            self._require_misconduct_admin()
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
            student_id = int(kwargs.get("student_id") or 0) or False
        except (TypeError, ValueError):
            student_id = False
        students = self._students_for_company(company)
        student = students.filtered(lambda item: item.id == student_id)[:1]
        form_values = {name: "" for name in CASE_CHAR_FIELDS + CASE_TEXT_FIELDS + CASE_SELECTION_FIELDS}
        form_values.update({name: False for name in CASE_BOOL_FIELDS})
        form_values.update(
            {
                "date": fields.Date.context_today(request.env.user),
                "birthdate": student.birthdate if student else "",
                "name": student.name if student else "",
                "gender": student.gender if student else "",
                "nationality": student.nationality if student else "",
                "class_id": student.class_id.id if student and student.class_id else False,
                "div_id": student.div.id if student and student.div else False,
                "siblings_count": 0,
            }
        )
        family_lines = [
            {"id": False, "relation_type": "father", "name": "", "age": 0, "education": "", "job": "", "economic_level": ""},
            {"id": False, "relation_type": "mother", "name": "", "age": 0, "education": "", "job": "", "economic_level": ""},
            {"id": False, "relation_type": "other", "name": "", "age": 0, "education": "", "job": "", "economic_level": ""},
        ]
        return request.render(
            "attendance_location_portal.portal_student_case_study_form",
            self._case_form_context(
                page_name="portal_case_study_new",
                companies=companies,
                company=company,
                students=students,
                student=student,
                case=False,
                form_values=form_values,
                family_lines=family_lines,
                active_tab=kwargs.get("tab") or "demographic",
                error_message=kwargs.get("error"),
            ),
        )

    @http.route(
        "/my/case_studies/submit",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_case_study_submit(self, **post):
        try:
            self._require_misconduct_admin()
        except AccessError as error:
            return self._failed_page(str(error))
        companies = self._allowed_companies()
        try:
            company_id = int(post.get("company_id") or 0)
            student_id = int(post.get("student_id") or 0)
        except (TypeError, ValueError):
            return request.redirect(
                "/my/case_studies/new?%s" % urlencode({"error": _("Invalid form values.")})
            )
        company = companies.filtered(lambda item: item.id == company_id)[:1]
        if not company or not student_id:
            return request.redirect(
                "/my/case_studies/new?%s"
                % urlencode({"error": _("Company and student are required."), "company_id": company_id})
            )
        try:
            vals = self._vals_from_post(post, company_id=company.id)
            vals["student_id"] = student_id
            if not vals.get("date"):
                vals["date"] = fields.Date.context_today(request.env.user)
            vals["family_member_ids"] = self._family_commands_from_post(post)
            case = request.env["student.case.study"].sudo().create(vals)
            return request.redirect(
                "/my/case_studies/%s?%s"
                % (case.id, urlencode({"message": _("Case study created.")}))
            )
        except (UserError, ValidationError, ValueError) as error:
            return request.redirect(
                "/my/case_studies/new?%s"
                % urlencode({"error": str(error), "company_id": company_id, "student_id": student_id})
            )
        except Exception as error:
            _logger.exception("Portal case study create failed: %s", error)
            return request.redirect(
                "/my/case_studies/new?%s"
                % urlencode({"error": _("Could not create the case study."), "company_id": company_id})
            )

    @http.route(
        "/my/case_studies/<int:case_id>",
        type="http",
        auth="user",
        website=True,
    )
    def portal_case_study_detail(self, case_id, **kwargs):
        try:
            case = self._get_case(case_id)
        except AccessError as error:
            return self._failed_page(str(error))
        companies = self._allowed_companies()
        students = self._students_for_company(case.company_id)
        form_values = {}
        for name in CASE_CHAR_FIELDS + CASE_TEXT_FIELDS + CASE_SELECTION_FIELDS:
            form_values[name] = case[name] or ""
        for name in CASE_BOOL_FIELDS:
            form_values[name] = bool(case[name])
        for name in CASE_DATE_FIELDS:
            form_values[name] = case[name] or ""
        for name in CASE_INT_FIELDS:
            form_values[name] = case[name] or 0
        form_values["class_id"] = case.class_id.id if case.class_id else False
        form_values["div_id"] = case.div_id.id if case.div_id else False
        family_lines = [
            {
                "id": line.id,
                "relation_type": line.relation_type or "",
                "name": line.name or "",
                "age": line.age or 0,
                "education": line.education or "",
                "job": line.job or "",
                "economic_level": line.economic_level or "",
            }
            for line in case.family_member_ids
        ] or [
            {"id": False, "relation_type": "father", "name": "", "age": 0, "education": "", "job": "", "economic_level": ""},
            {"id": False, "relation_type": "mother", "name": "", "age": 0, "education": "", "job": "", "economic_level": ""},
        ]
        return request.render(
            "attendance_location_portal.portal_student_case_study_form",
            self._case_form_context(
                page_name="portal_case_study_detail",
                companies=companies,
                company=case.company_id,
                students=students,
                student=case.student_id,
                case=case,
                form_values=form_values,
                family_lines=family_lines,
                active_tab=kwargs.get("tab") or "demographic",
                message=kwargs.get("message"),
                error_message=kwargs.get("error"),
            ),
        )

    @http.route(
        "/my/case_studies/<int:case_id>/save",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_case_study_save(self, case_id, **post):
        try:
            case = self._get_case(case_id)
        except AccessError as error:
            return self._failed_page(str(error))
        tab = post.get("tab") or "demographic"
        try:
            vals = self._vals_from_post(post)
            vals["family_member_ids"] = self._family_commands_from_post(
                post, existing=case.family_member_ids
            )
            case.write(vals)
            params = {"message": _("Case study saved."), "tab": tab}
        except (UserError, ValidationError, ValueError) as error:
            params = {"error": str(error), "tab": tab}
        except Exception as error:
            _logger.exception("Portal case study save failed: %s", error)
            params = {"error": _("Could not save the case study."), "tab": tab}
        return request.redirect("/my/case_studies/%s?%s" % (case.id, urlencode(params)))

    @http.route(
        "/my/case_studies/<int:case_id>/delete",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_case_study_delete(self, case_id, **post):
        try:
            case = self._get_case(case_id)
        except AccessError as error:
            return self._failed_page(str(error))
        try:
            case.unlink()
            return request.redirect(
                "/my/case_studies?%s" % urlencode({"message": _("Case study deleted.")})
            )
        except Exception as error:
            _logger.exception("Portal case study delete failed: %s", error)
            return request.redirect(
                "/my/case_studies/%s?%s"
                % (case_id, urlencode({"error": _("Could not delete the case study.")}))
            )

    @http.route(
        "/my/case_studies/<int:case_id>/print",
        type="http",
        auth="user",
        website=True,
    )
    def portal_case_study_print(self, case_id, **kwargs):
        try:
            case = self._get_case(case_id)
        except AccessError as error:
            return self._failed_page(str(error))
        try:
            # Portal users cannot read ir.actions.report; resolve + render as sudo.
            report = (
                request.env["ir.actions.report"]
                .sudo()
                .search(
                    [("report_name", "=", "jt_student_violations.report_student_case_study")],
                    limit=1,
                )
            )
            if not report:
                raise UserError(_("Case study report is not available."))
            pdf_content, _unused = report.with_context(lang="ar_001")._render_qweb_pdf(
                report.report_name, res_ids=case.ids
            )
            filename = "Case_Study_%s.pdf" % (case.name or case.student_id.name or case.id)
            return request.make_response(
                pdf_content,
                headers=[
                    ("Content-Type", "application/pdf"),
                    ("Content-Length", len(pdf_content)),
                    ("Content-Disposition", content_disposition(filename)),
                ],
            )
        except (UserError, ValidationError) as error:
            return request.redirect(
                "/my/case_studies/%s?%s" % (case_id, urlencode({"error": str(error)}))
            )
        except Exception as error:
            _logger.exception("Portal case study print failed: %s", error)
            return request.redirect(
                "/my/case_studies/%s?%s"
                % (case_id, urlencode({"error": _("Could not print the case study.")}))
            )
