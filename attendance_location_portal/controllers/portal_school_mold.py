import base64
import logging
from urllib.parse import urlencode, quote

from odoo import _, fields, http
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.http import request
from odoo.addons.portal.controllers.portal import pager as portal_pager

from .portal_common import PortalHrMixin

_logger = logging.getLogger(__name__)

MOLD_STATE_LABELS = {
    "draft": "Draft",
    "done": "Done",
}

MOLD_STATE_BADGES = {
    "draft": "text-bg-secondary",
    "done": "text-bg-success",
}

EDITABLE_COL_TYPES = {
    "score",
    "text",
    "seat_number",
    "pin_number",
    "class",
}


class PortalSchoolMoldController(PortalHrMixin, http.Controller):
    def _require_mold_admin(self):
        if not self._is_portal_mold_admin():
            raise AccessError(_("You are not allowed to manage school molds."))

    def _failed_page(self, message):
        return request.render(
            "attendance_location_portal.portal_school_mold_failed_page",
            {
                "page_name": "portal_school_mold_failed",
                "error_message": message,
            },
        )

    def _allowed_companies(self):
        return request.env.user.company_ids.sorted("name")

    def _state_labels(self):
        return {key: request.env._(label) for key, label in MOLD_STATE_LABELS.items()}

    def _selection_label(self, record, field_name):
        field = record._fields.get(field_name)
        if not field or field.type != "selection":
            return ""
        value = record[field_name]
        if not value:
            return ""
        return dict(field._description_selection(record.env)).get(value, value)

    def _can_access_mold(self, mold):
        company_ids = set(self._portal_user_company_ids())
        if (
            not mold.exists()
            or not mold.company_id
            or mold.company_id.id not in company_ids
        ):
            return False
        if self._is_portal_mold_admin():
            return True
        # Exam admins may open the result generated from an exam they can see.
        if self._is_portal_exam_admin() and mold.exam_id:
            exam = mold.exam_id.sudo()
            return bool(exam.company_id and exam.company_id.id in company_ids)
        return False

    def _get_school_mold(self, mold_id, require_write=False):
        mold = request.env["school.mold"].sudo().browse(mold_id)
        if not self._can_access_mold(mold):
            raise AccessError(_("This result does not exist or is not accessible."))
        if require_write and not self._is_portal_mold_admin():
            raise AccessError(_("You are not allowed to edit school molds."))
        return mold

    def _build_header_groups(self, columns):
        """Build two-row header: group spans + column names (RTL-friendly)."""
        groups = []
        current = None
        for column in columns:
            group_name = column.group_name or ""
            if current and current["name"] == group_name:
                current["span"] += 1
                current["columns"].append(column)
            else:
                current = {
                    "name": group_name,
                    "span": 1,
                    "color": column.color or "#FFFFFF",
                    "columns": [column],
                }
                groups.append(current)
        return groups

    def _line_cell_value(self, line, column):
        return line._cell_value(column)

    def _is_cell_editable(self, column, mold_editable):
        return mold_editable and column.col_type in EDITABLE_COL_TYPES

    def _years(self):
        return request.env["year.year"].sudo().search([], order="name desc, id desc")

    def _classes(self):
        return request.env["student.class"].sudo().search([], order="name, id")

    def _selection_options(self, model_name, field_name):
        field = request.env[model_name]._fields.get(field_name)
        if not field or field.type != "selection":
            return []
        return field._description_selection(request.env)

    def _allowed_term_types(self, term):
        Mold = request.env["school.mold"].sudo()
        options = self._selection_options("school.mold", "term_types")
        try:
            from odoo.addons.school_molds_generator.models.school_mold import (
                BASE_TERM_TYPE_KEYS,
                FIRST_TERM_ONLY_TYPE_KEYS,
            )
        except Exception:
            return options
        allowed = list(BASE_TERM_TYPE_KEYS)
        if (term or "first") == "first":
            allowed.extend(FIRST_TERM_ONLY_TYPE_KEYS)
        allowed_set = set(allowed)
        return [item for item in options if item[0] in allowed_set]

    def _new_form_values(self, **extra):
        companies = self._allowed_companies()
        term = extra.get("term") or "first"
        term_types = extra.get("term_types") or "industrial_electricity"
        allowed_types = self._allowed_term_types(term)
        if term_types not in {key for key, _label in allowed_types}:
            term_types = allowed_types[0][0] if allowed_types else "industrial_electricity"
        return {
            "page_name": "portal_school_mold_new",
            "companies": companies,
            "company": extra.get("company") or companies[:1],
            "years": self._years(),
            "classes": self._classes(),
            "term_options": self._selection_options("school.mold", "term"),
            "term_type_options": allowed_types,
            "exam_type_options": self._selection_options("school.mold", "exam_type"),
            "term": term,
            "term_types": term_types,
            "exam_type": extra.get("exam_type") or "monthly",
            "year_id": extra.get("year_id") or "",
            "class_id": extra.get("class_id") or "",
            "date": extra.get("date") or fields.Date.context_today(request.env.user),
            "load_students": extra.get("load_students", True),
            "error_message": extra.get("error_message"),
        }

    @http.route(
        ["/my/school_molds", "/my/school_molds/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_school_molds(
        self,
        page=1,
        sortby=None,
        filterby=None,
        search=None,
        search_in="all",
        **kwargs,
    ):
        try:
            self._require_mold_admin()
        except AccessError as error:
            return self._failed_page(str(error))

        companies = self._allowed_companies()
        mold_model = request.env["school.mold"].sudo()
        domain = self._portal_company_domain() + [("mold_kind", "=", "grades")]

        searchbar_filters = self._portal_company_searchbar_filters(
            companies,
            base={
                "all": {"label": _("All"), "domain": [], "sequence": 10},
                "draft": {
                    "label": _("Draft"),
                    "domain": [("state", "=", "draft")],
                    "sequence": 20,
                },
                "done": {
                    "label": _("Done"),
                    "domain": [("state", "=", "done")],
                    "sequence": 30,
                },
            },
        )
        search_inputs = self._portal_student_searchbar_inputs(
            name_fields=[
                "line_ids.student_name",
                "line_ids.student_id.name",
            ],
            id_fields=["line_ids.student_id.stud_id"],
            extra_all_domains=lambda value: [
                [("name", "ilike", value)],
                [("exam_id.name", "ilike", value)],
                [("class_id.name", "ilike", value)],
                [("year_id.name", "ilike", value)],
            ],
            extra_inputs={
                "result": {
                    "input": "result",
                    "label": _("Search in Result"),
                    "sequence": 40,
                    "domain": lambda value: [("name", "ilike", value)],
                },
            },
        )
        searchbar_sortings = {
            "date": {"label": _("Newest"), "order": "date desc, id desc"},
            "name": {"label": _("Result"), "order": "name, id desc"},
            "state": {"label": _("Status"), "order": "state, date desc"},
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
        mold_count = mold_model.search_count(domain)
        pager = portal_pager(
            url="/my/school_molds",
            url_args={
                "sortby": searchbar["sortby"],
                "filterby": searchbar["filterby"],
                "search": searchbar["search"],
                "search_in": searchbar["search_in"],
            },
            total=mold_count,
            page=page,
            step=self._items_per_page,
        )
        molds = mold_model.search(
            domain,
            order=searchbar["order"],
            limit=self._items_per_page,
            offset=pager["offset"],
        )
        return request.render(
            "attendance_location_portal.portal_my_school_molds",
            {
                "page_name": "portal_school_molds",
                "molds": molds,
                "pager": pager,
                "show_company": len(companies) > 1,
                "state_labels": self._state_labels(),
                "state_badges": MOLD_STATE_BADGES,
                "selection_label": self._selection_label,
                "default_url": "/my/school_molds",
                "searchbar_filters": searchbar["searchbar_filters"],
                "filterby": searchbar["filterby"],
                "searchbar_inputs": searchbar["searchbar_inputs"],
                "search_in": searchbar["search_in"],
                "search": searchbar["search"],
                "searchbar_sortings": searchbar["searchbar_sortings"],
                "sortby": searchbar["sortby"],
            },
        )

    @http.route("/my/school_molds/new", type="http", auth="user", website=True)
    def portal_school_mold_new(self, **kwargs):
        try:
            self._require_mold_admin()
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

        load_students = kwargs.get("load_students")
        if load_students is None:
            load_students = True
        else:
            load_students = str(load_students).lower() in ("1", "true", "yes", "on")

        return request.render(
            "attendance_location_portal.portal_school_mold_new",
            self._new_form_values(
                company=company,
                term=kwargs.get("term") or "first",
                term_types=kwargs.get("term_types") or "industrial_electricity",
                exam_type=kwargs.get("exam_type") or "monthly",
                year_id=kwargs.get("year_id") or "",
                class_id=kwargs.get("class_id") or "",
                date=kwargs.get("date") or fields.Date.context_today(request.env.user),
                load_students=load_students,
                error_message=kwargs.get("error"),
            ),
        )

    @http.route(
        "/my/school_molds/submit",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_school_mold_submit(self, **post):
        try:
            self._require_mold_admin()
        except AccessError as error:
            return self._failed_page(str(error))

        companies = self._allowed_companies()
        try:
            company_id = int(post.get("company_id") or 0)
            year_id = int(post.get("year_id") or 0) or False
            class_id = int(post.get("class_id") or 0) or False
        except (TypeError, ValueError):
            return request.redirect(
                "/my/school_molds/new?%s"
                % urlencode({"error": _("Invalid result values.")})
            )

        company = companies.filtered(lambda item: item.id == company_id)[:1]
        if not company:
            return self._failed_page(_("This company is not in your allowed companies."))

        term = (post.get("term") or "first").strip()
        term_types = (post.get("term_types") or "industrial_electricity").strip()
        exam_type = (post.get("exam_type") or "monthly").strip()
        date_value = (post.get("date") or "").strip() or fields.Date.context_today(
            request.env.user
        )
        load_students = bool(post.get("load_students"))

        allowed_terms = {key for key, _label in self._selection_options("school.mold", "term")}
        allowed_types = {key for key, _label in self._allowed_term_types(term)}
        allowed_exam_types = {
            key for key, _label in self._selection_options("school.mold", "exam_type")
        }
        if term not in allowed_terms or term_types not in allowed_types:
            return request.redirect(
                "/my/school_molds/new?%s"
                % urlencode(
                    {
                        "company_id": company.id,
                        "error": _("Please select a valid term and specialization."),
                    }
                )
            )
        if exam_type not in allowed_exam_types:
            exam_type = "monthly"

        year = self._years().filtered(lambda item: item.id == year_id)[:1]
        class_rec = self._classes().filtered(lambda item: item.id == class_id)[:1]

        try:
            mold = (
                request.env["school.mold"]
                .sudo()
                .create(
                    {
                        "mold_kind": "grades",
                        "company_id": company.id,
                        "term": term,
                        "term_types": term_types,
                        "exam_type": exam_type,
                        "year_id": year.id if year else False,
                        "class_id": class_rec.id if class_rec else False,
                        "date": date_value,
                    }
                )
            )
            if load_students:
                mold.action_load_students()
            return request.redirect(
                "/my/school_molds/%s?%s"
                % (mold.id, urlencode({"message": _("Result created.")}))
            )
        except (UserError, ValidationError) as error:
            return request.redirect(
                "/my/school_molds/new?%s"
                % urlencode(
                    {
                        "company_id": company.id,
                        "term": term,
                        "term_types": term_types,
                        "exam_type": exam_type,
                        "year_id": year.id if year else "",
                        "class_id": class_rec.id if class_rec else "",
                        "date": date_value,
                        "load_students": "1" if load_students else "0",
                        "error": str(error),
                    }
                )
            )
        except Exception as error:
            _logger.exception("Portal school mold create failed: %s", error)
            return request.redirect(
                "/my/school_molds/new?%s"
                % urlencode({"error": _("Could not create the result.")})
            )

    @http.route(
        "/my/school_molds/<int:mold_id>",
        type="http",
        auth="user",
        website=True,
    )
    def portal_school_mold_detail(self, mold_id, **kwargs):
        try:
            mold = self._get_school_mold(mold_id)
        except AccessError as error:
            return self._failed_page(str(error))

        columns = mold.column_ids.sorted(lambda col: (col.sequence, col.id))
        lines = mold.line_ids.sorted(lambda line: (line.sequence, line.id))
        mold_editable = mold.state == "draft" and self._is_portal_mold_admin()
        return request.render(
            "attendance_location_portal.portal_school_mold_detail",
            {
                "page_name": "portal_school_mold_detail",
                "mold": mold,
                "columns": columns,
                "header_groups": self._build_header_groups(columns),
                "lines": lines,
                "mold_editable": mold_editable,
                "can_write": self._is_portal_mold_admin(),
                "state_labels": self._state_labels(),
                "state_badges": MOLD_STATE_BADGES,
                "selection_label": self._selection_label,
                "cell_value": self._line_cell_value,
                "is_cell_editable": self._is_cell_editable,
                "message": kwargs.get("message"),
                "error_message": kwargs.get("error"),
            },
        )

    @http.route(
        "/my/school_molds/<int:mold_id>/save",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_school_mold_save(self, mold_id, **post):
        try:
            mold = self._get_school_mold(mold_id, require_write=True)
        except AccessError as error:
            return self._failed_page(str(error))
        if mold.state != "draft":
            return request.redirect(
                "/my/school_molds/%s?%s"
                % (mold.id, urlencode({"error": _("This result is done and cannot be modified.")}))
            )

        columns = {
            column.key: column
            for column in mold.column_ids
            if column.col_type in EDITABLE_COL_TYPES
        }
        try:
            for line in mold.line_ids:
                values = dict(line.values_json or {})
                student_name = line.student_name or ""
                changed = False
                for key, column in columns.items():
                    form_key = "cell_%s_%s" % (line.id, key)
                    if form_key not in post:
                        continue
                    raw = (post.get(form_key) or "").strip()
                    if column.col_type == "name":
                        continue
                    if values.get(key, "") != raw:
                        values[key] = raw
                        changed = True
                name_key = "cell_%s__student_name" % line.id
                if name_key in post:
                    new_name = (post.get(name_key) or "").strip()
                    if new_name != (line.student_name or ""):
                        student_name = new_name
                        changed = True
                if changed:
                    line.write(
                        {
                            "values_json": values,
                            "student_name": student_name,
                        }
                    )
            mold.line_ids._recompute_totals(mold.column_ids)
            params = {"message": _("Sheet saved.")}
        except (UserError, ValidationError) as error:
            params = {"error": str(error)}
        except Exception as error:
            _logger.exception("Portal school mold save failed: %s", error)
            params = {"error": _("Could not save the sheet.")}
        return request.redirect("/my/school_molds/%s?%s" % (mold.id, urlencode(params)))

    @http.route(
        "/my/school_molds/<int:mold_id>/action",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_school_mold_action(self, mold_id, **post):
        try:
            mold = self._get_school_mold(mold_id, require_write=True)
        except AccessError as error:
            return self._failed_page(str(error))

        action = (post.get("mold_action") or "").strip()
        line_id = 0
        if action.startswith("delete_line:"):
            try:
                line_id = int(action.split(":", 1)[1])
            except (TypeError, ValueError):
                line_id = 0
            action = "delete_line"
        params = {}
        try:
            if action == "load_students" and mold.state == "draft":
                mold.action_load_students()
                params["message"] = _("Students loaded.")
            elif action == "add_rows" and mold.state == "draft":
                mold.action_add_empty_rows()
                params["message"] = _("10 rows added.")
            elif action == "recompute" and mold.state == "draft":
                mold.action_recompute_totals()
                params["message"] = _("Totals recomputed.")
            elif action == "mark_done" and mold.state == "draft":
                mold.action_mark_done()
                params["message"] = _("Result marked as done.")
            elif action == "reset_draft" and mold.state == "done":
                mold.action_reset_draft()
                params["message"] = _("Result reset to draft.")
            elif action == "delete_line" and mold.state == "draft":
                line = mold.line_ids.filtered(lambda item: item.id == line_id)[:1]
                if line:
                    line.unlink()
                    params["message"] = _("Row deleted.")
                else:
                    params["error"] = _("Row not found.")
            elif action == "delete":
                mold.unlink()
                return request.redirect("/my/school_molds")
            else:
                params["error"] = _("This action is not available.")
        except (UserError, ValidationError) as error:
            params["error"] = str(error)
        except Exception as error:
            _logger.exception("Portal school mold action failed: %s", error)
            params["error"] = _("Could not update the result.")
        return request.redirect("/my/school_molds/%s?%s" % (mold.id, urlencode(params)))

    @http.route(
        "/my/school_molds/<int:mold_id>/xlsx",
        type="http",
        auth="user",
        website=True,
    )
    def portal_school_mold_xlsx(self, mold_id, **kwargs):
        try:
            mold = self._get_school_mold(mold_id)
        except AccessError:
            return request.not_found()

        content, filename = mold._generate_xlsx()
        mold.sudo().write(
            {
                "xlsx_file": base64.b64encode(content),
                "xlsx_filename": filename,
            }
        )
        safe_name = (filename or "result.xlsx").replace('"', "")
        return request.make_response(
            content,
            headers=[
                (
                    "Content-Type",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
                ("Content-Length", len(content)),
                (
                    "Content-Disposition",
                    "attachment; filename*=UTF-8''%s" % quote(safe_name),
                ),
            ],
        )

    @http.route(
        "/my/school_molds/<int:mold_id>/upload_xlsx",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_school_mold_upload_xlsx(self, mold_id, **post):
        try:
            mold = self._get_school_mold(mold_id, require_write=True)
        except AccessError as error:
            return self._failed_page(str(error))

        if mold.state != "draft":
            return request.redirect(
                "/my/school_molds/%s?%s"
                % (
                    mold.id,
                    urlencode({"error": _("This result is done and cannot be modified.")}),
                )
            )

        upload = request.httprequest.files.get("excel_file")
        filename = (upload.filename if upload else "") or ""
        if not upload or not filename:
            return request.redirect(
                "/my/school_molds/%s?%s"
                % (mold.id, urlencode({"error": _("Please select an Excel file (.xlsx).")}))
            )
        if not filename.lower().endswith((".xlsx", ".xlsm")):
            return request.redirect(
                "/my/school_molds/%s?%s"
                % (mold.id, urlencode({"error": _("Only .xlsx Excel files are supported.")}))
            )

        try:
            raw = upload.read()
            count = mold.action_import_xlsx(raw, filename)
            params = {"message": _("%s row(s) loaded from Excel.") % count}
        except (UserError, ValidationError) as error:
            params = {"error": str(error)}
        except Exception as error:
            _logger.exception("Portal school mold Excel upload failed: %s", error)
            params = {"error": _("Could not import the Excel file.")}
        return request.redirect("/my/school_molds/%s?%s" % (mold.id, urlencode(params)))
