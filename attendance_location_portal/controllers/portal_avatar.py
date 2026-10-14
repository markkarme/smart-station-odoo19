import base64

from odoo import http
from odoo.http import request
from odoo.tools.image import image_process

MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"}


class PortalAvatarController(http.Controller):
    @http.route(
        "/my/account/image",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
    )
    def portal_account_image(self, image=None, redirect="/my/home", **post):
        redirect_url = redirect if isinstance(redirect, str) and redirect.startswith("/my") else "/my/home"
        uploaded = image or request.httprequest.files.get("image")

        def fail(code):
            return request.redirect(self._image_redirect(redirect_url, "image_error", code))

        if not uploaded or not getattr(uploaded, "filename", None):
            return fail("type")
        if (uploaded.mimetype or "").lower() not in ALLOWED_IMAGE_TYPES:
            return fail("type")
        data = uploaded.read()
        if not data:
            return fail("type")
        if len(data) > MAX_IMAGE_BYTES:
            return fail("size")
        try:
            processed = image_process(data, size=(1920, 1920), verify_resolution=False)
        except Exception:
            return fail("type")
        if not processed:
            return fail("type")

        encoded = base64.b64encode(processed)
        user = request.env.user.sudo()
        user.write({"image_1920": encoded})
        employees = request.env["hr.employee"].sudo().search([
            "|",
            ("user_id", "=", user.id),
            ("work_contact_id", "=", user.partner_id.id),
        ])
        if employees:
            employees.write({"image_1920": encoded})
        return request.redirect(self._image_redirect(redirect_url, "image_updated", "1"))

    def _image_redirect(self, redirect_url, key, value):
        separator = "&" if "?" in redirect_url else "?"
        return "%s%s%s=%s" % (redirect_url, separator, key, value)
