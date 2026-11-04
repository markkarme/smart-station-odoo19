# -*- coding: utf-8 -*-
import base64
import io
import zipfile
from xml.etree import ElementTree as ET

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from werkzeug.urls import url_quote


class HrAppraisalJobDescription(models.Model):
    _name = "hr.appraisal.job.description"
    _description = "الوصف الوظيفي ومؤشرات الأداء"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name, id"

    name = fields.Char(string="الاسم", required=True, tracking=True)
    file = fields.Binary(string="الملف", attachment=True)
    file_name = fields.Char(string="اسم الملف")
    file_mimetype = fields.Char(string="نوع الملف", compute="_compute_file_meta")
    is_pdf = fields.Boolean(compute="_compute_file_meta")
    is_image = fields.Boolean(compute="_compute_file_meta")
    is_docx = fields.Boolean(compute="_compute_file_meta")
    company_id = fields.Many2one(
        "res.company",
        string="الشركة",
        default=lambda self: self.env.company,
        index=True,
        tracking=True,
    )
    active = fields.Boolean(string="نشط", default=True)

    def _get_file_attachment(self):
        self.ensure_one()
        if not self.id:
            return self.env["ir.attachment"]
        return (
            self.env["ir.attachment"]
            .sudo()
            .search(
                [
                    ("res_model", "=", self._name),
                    ("res_id", "=", self.id),
                    ("res_field", "=", "file"),
                ],
                limit=1,
            )
        )

    def _get_file_bytes(self):
        self.ensure_one()
        data = self.with_context(bin_size=False).file
        if not data:
            return b""
        if isinstance(data, bytes):
            try:
                return base64.b64decode(data, validate=True)
            except Exception:
                return data
        if isinstance(data, str):
            return base64.b64decode(data)
        return b""

    def _get_file_b64(self):
        self.ensure_one()
        data = self.with_context(bin_size=False).file
        if not data:
            return False
        if isinstance(data, str):
            return data
        if isinstance(data, bytes):
            try:
                base64.b64decode(data, validate=True)
                return data.decode()
            except Exception:
                return base64.b64encode(data).decode()
        return False

    @api.depends("file", "file_name")
    def _compute_file_meta(self):
        for rec in self:
            attachment = rec._get_file_attachment()
            mimetype = attachment.mimetype or ""
            fname = (rec.file_name or "").lower()
            rec.file_mimetype = mimetype
            rec.is_pdf = mimetype == "application/pdf" or fname.endswith(".pdf")
            rec.is_image = mimetype.startswith("image/")
            rec.is_docx = (
                fname.endswith(".docx")
                or mimetype
                == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

    def _docx_to_preview_html(self):
        self.ensure_one()
        raw = self._get_file_bytes()
        if not raw:
            return False
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                xml_bytes = archive.read("word/document.xml")
        except Exception:
            return False
        try:
            root = ET.fromstring(xml_bytes)
        except ET.ParseError:
            return False

        paragraphs = []
        for para in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
            texts = [
                node.text
                for node in para.iter(
                    "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"
                )
                if node.text
            ]
            line = "".join(texts).strip()
            if line:
                paragraphs.append(line)
        if not paragraphs:
            return False
        return "".join(
            f'<p style="margin:0 0 0.6rem 0; line-height:1.6; direction:rtl; text-align:right;">'
            f"{self._escape(p)}</p>"
            for p in paragraphs
        )

    @staticmethod
    def _escape(text):
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    def _post_file_to_chatter(self):
        """Post a chatter message with a clickable attachment (Documents-style)."""
        Attachment = self.env["ir.attachment"].sudo()
        for rec in self:
            if not rec.file:
                continue

            filename = rec.file_name or rec.name or "file"
            field_att = rec._get_file_attachment()
            datas = rec._get_file_b64()
            if not datas and not field_att:
                continue

            # Create a normal attachment (no res_field) so chatter can preview/open it
            values = {
                "name": filename,
                "res_model": rec._name,
                "res_id": rec.id,
                "type": "binary",
            }
            if field_att:
                values.update(
                    {
                        "datas": field_att.datas,
                        "mimetype": field_att.mimetype,
                    }
                )
            else:
                values["datas"] = datas

            chatter_att = Attachment.create(values)
            rec.message_post(
                body=_("تم إرفاق الملف: %s", filename),
                attachment_ids=[chatter_att.id],
                subtype_xmlid="mail.mt_note",
            )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.filtered("file")._post_file_to_chatter()
        return records

    def write(self, vals):
        res = super().write(vals)
        if "file" in vals and vals.get("file"):
            self._post_file_to_chatter()
        return res

    def action_view_file(self):
        """Open the native Odoo FileViewer (same UX as Documents / chatter)."""
        self.ensure_one()
        if not self.id or not self.file:
            raise UserError(_("احفظ السجل أولاً ثم ارفع ملفاً لعرضه."))

        filename = self.file_name or self.name or "file"
        return {
            "type": "ir.actions.client",
            "tag": "ss_job_description_file_viewer",
            "params": {
                "res_id": self.id,
                "filename": filename,
                "mimetype": self.file_mimetype or "",
                "is_pdf": self.is_pdf,
                "is_image": self.is_image,
                "is_docx": self.is_docx,
                "content_url": (
                    f"/web/content/{self._name}/{self.id}/file/{url_quote(filename)}"
                ),
                "preview_url": f"/smart_station_appraisals/job_description/{self.id}/preview",
            },
        }
