import logging
from urllib.parse import urlencode

from markupsafe import Markup
from odoo import _, http
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.addons.portal.controllers.portal import pager as portal_pager
from werkzeug.urls import url_quote

from .portal_common import PortalHrMixin

_logger = logging.getLogger(__name__)


class PortalJobDescriptionController(PortalHrMixin, http.Controller):
    def _require_job_description_admin(self):
        if not self._is_portal_job_description_admin():
            raise AccessError(
                _("You are not allowed to manage job descriptions.")
            )

    def _failed_page(self, message):
        return request.render(
            "attendance_location_portal.portal_job_description_failed_page",
            {
                "page_name": "portal_job_description_failed",
                "error_message": message,
            },
        )

    def _allowed_companies(self):
        return request.env.user.company_ids.sorted("name")

    def _get_record(self, record_id):
        self._require_job_description_admin()
        record = request.env["hr.appraisal.job.description"].sudo().browse(record_id)
        company_ids = set(self._portal_user_company_ids())
        if (
            not record.exists()
            or (record.company_id and record.company_id.id not in company_ids)
        ):
            raise AccessError(
                _("This job description does not exist or is not accessible.")
            )
        return record

    def _file_preview_values(self, record):
        if not record or not record.file:
            return {
                "has_file_preview": False,
                "file_content_url": False,
                "file_preview_url": False,
                "docx_preview_html": False,
            }
        filename = record.file_name or record.name or "file"
        content_url = "/web/content/%s/%s/file/%s?download=false" % (
            record._name,
            record.id,
            url_quote(filename),
        )
        preview_url = "/my/job_descriptions/%s/preview" % record.id
        docx_html = False
        if record.is_docx:
            raw_html = record._docx_to_preview_html()
            docx_html = Markup(raw_html) if raw_html else False
        return {
            "has_file_preview": True,
            "file_content_url": content_url,
            "file_preview_url": preview_url,
            "docx_preview_html": docx_html,
        }

    def _form_values(self, **extra):
        companies = self._allowed_companies()
        record = extra.get("record")
        values = {
            "companies": companies,
            "show_company": len(companies) > 1,
            "default_company_id": companies[:1].id if companies else False,
            **extra,
        }
        values.update(self._file_preview_values(record))
        return values

    def _redirect_list(self, **params):
        query = urlencode({k: v for k, v in params.items() if v})
        return request.redirect(
            "/my/job_descriptions%s" % (("?%s" % query) if query else "")
        )

    @http.route(
        ["/my/job_descriptions", "/my/job_descriptions/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_job_descriptions(
        self,
        page=1,
        sortby=None,
        filterby=None,
        search=None,
        search_in="all",
        **kwargs,
    ):
        try:
            self._require_job_description_admin()
        except AccessError as error:
            return self._failed_page(str(error))

        companies = self._allowed_companies()
        JobDescription = request.env["hr.appraisal.job.description"].sudo()
        domain = self._portal_company_domain()
        searchbar_filters = self._portal_company_searchbar_filters(
            companies,
            base={"all": {"label": _("All"), "domain": [], "sequence": 10}},
        )
        searchbar_inputs = {
            "all": {
                "input": "all",
                "label": _("Search in All"),
                "sequence": 10,
                "domain": lambda value: self._portal_or_domain(
                    [
                        [("name", "ilike", value)],
                        [("file_name", "ilike", value)],
                    ]
                ),
            },
            "name": {
                "input": "name",
                "label": _("Search in Name"),
                "sequence": 20,
                "domain": lambda value: [("name", "ilike", value)],
            },
            "file": {
                "input": "file",
                "label": _("Search in File"),
                "sequence": 30,
                "domain": lambda value: [("file_name", "ilike", value)],
            },
        }
        searchbar_sortings = {
            "name": {"label": _("Name"), "order": "name, id"},
            "newest": {"label": _("Newest"), "order": "id desc"},
        }
        searchbar = self._portal_apply_searchbar(
            domain,
            searchbar_filters=searchbar_filters,
            searchbar_inputs=searchbar_inputs,
            searchbar_sortings=searchbar_sortings,
            filterby=filterby,
            search=search,
            search_in=search_in,
            sortby=sortby,
            default_filterby="all",
            default_search_in="all",
            default_sortby="name",
        )
        domain = searchbar["domain"]
        total = JobDescription.search_count(domain)
        pager = portal_pager(
            url="/my/job_descriptions",
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
        records = JobDescription.search(
            domain,
            order=searchbar["order"],
            limit=self._items_per_page,
            offset=pager["offset"],
        )
        return request.render(
            "attendance_location_portal.portal_my_job_descriptions",
            {
                "page_name": "portal_job_descriptions",
                "records": records,
                "pager": pager,
                "show_company": len(companies) > 1,
                "default_url": "/my/job_descriptions",
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

    @http.route(
        [
            "/my/job_descriptions/new",
            "/my/job_descriptions/create",
            "/my/job_descriptions/<int:record_id>/save",
            "/my/job_descriptions/<int:record_id>/delete",
        ],
        type="http",
        auth="user",
        website=True,
    )
    def portal_job_description_write_forbidden(self, record_id=None, **kwargs):
        return self._redirect_list(
            error=_("You are not allowed to create, edit, or delete job descriptions.")
        )

    @http.route(
        "/my/job_descriptions/<int:record_id>",
        type="http",
        auth="user",
        website=True,
    )
    def portal_job_description_detail(self, record_id, **kwargs):
        try:
            record = self._get_record(record_id)
        except AccessError as error:
            return self._failed_page(str(error))
        return request.render(
            "attendance_location_portal.portal_job_description_form",
            self._form_values(
                page_name="portal_job_description_detail",
                record=record,
                form_values={},
                message=kwargs.get("message"),
                error_message=kwargs.get("error"),
            ),
        )

    @http.route(
        "/my/job_descriptions/<int:record_id>/download",
        type="http",
        auth="user",
        website=True,
    )
    def portal_job_description_download(self, record_id, **kwargs):
        try:
            record = self._get_record(record_id)
        except AccessError as error:
            return self._failed_page(str(error))
        if not record.file:
            return self._redirect_list(error=_("No file is attached."))
        filename = record.file_name or record.name or "file"
        return request.redirect(
            "/web/content/%s/%s/file/%s?download=true"
            % (record._name, record.id, url_quote(filename))
        )

    @http.route(
        "/my/job_descriptions/<int:record_id>/preview",
        type="http",
        auth="user",
        website=True,
    )
    def portal_job_description_preview(self, record_id, **kwargs):
        try:
            record = self._get_record(record_id)
        except AccessError as error:
            return self._failed_page(str(error))
        if not record.file:
            return self._redirect_list(error=_("No file is attached."))
        return request.redirect(
            "/smart_station_appraisals/job_description/%s/preview" % record.id
        )
