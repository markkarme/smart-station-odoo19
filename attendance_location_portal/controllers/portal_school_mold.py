import base64
import logging
from urllib.parse import urlencode, quote

from odoo import _, http
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

    @http.route(
        ["/my/school_molds", "/my/school_molds/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_school_molds(self, page=1, **kwargs):
        try:
            self._require_mold_admin()
        except AccessError as error:
            return self._failed_page(str(error))

        mold_model = request.env["school.mold"].sudo()
        domain = self._portal_company_domain() + [("mold_kind", "=", "grades")]
        mold_count = mold_model.search_count(domain)
        pager = portal_pager(
            url="/my/school_molds",
            total=mold_count,
            page=page,
            step=self._items_per_page,
        )
        molds = mold_model.search(
            domain,
            order="date desc, id desc",
            limit=self._items_per_page,
            offset=pager["offset"],
        )
        return request.render(
            "attendance_location_portal.portal_my_school_molds",
            {
                "page_name": "portal_school_molds",
                "molds": molds,
                "pager": pager,
                "show_company": len(self._allowed_companies()) > 1,
                "state_labels": self._state_labels(),
                "state_badges": MOLD_STATE_BADGES,
                "selection_label": self._selection_label,
            },
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
