# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class JobDescriptionController(http.Controller):
    @http.route(
        "/smart_station_appraisals/job_description/<int:res_id>/preview",
        type="http",
        auth="user",
        readonly=True,
    )
    def job_description_preview(self, res_id, **kwargs):
        """HTML preview page used inside the native Odoo FileViewer iframe."""
        record = request.env["hr.appraisal.job.description"].browse(res_id).exists()
        if not record:
            return request.not_found()
        record.check_access("read")

        if record.is_pdf or record.is_image:
            filename = record.file_name or record.name or "file"
            return request.redirect(
                f"/web/content/{record._name}/{record.id}/file/{filename}?download=false"
            )

        body = record._docx_to_preview_html() or "<p>لا توجد معاينة متاحة لهذا الملف.</p>"
        page = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{record.file_name or record.name or "preview"}</title>
<style>
  body {{
    margin: 0;
    padding: 1.5rem;
    font-family: Tahoma, Arial, sans-serif;
    background: #f8f9fa;
    color: #212529;
  }}
  .sheet {{
    max-width: 920px;
    margin: 0 auto;
    background: #fff;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    padding: 1.5rem 1.75rem;
    box-shadow: 0 0.125rem 0.25rem rgba(0,0,0,.05);
  }}
</style>
</head>
<body>
  <div class="sheet">{body}</div>
</body>
</html>"""
        return request.make_response(
            page,
            headers=[("Content-Type", "text/html; charset=utf-8")],
        )
