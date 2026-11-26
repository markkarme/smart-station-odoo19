# -*- coding: utf-8 -*-
"""Drop the portal fee-plan field from stored employee views.

The field is removed in this version. View validation runs before the new
view XML is loaded, so the old arch must be cleaned first.
"""
import json
import re

_FIELD_RE = re.compile(
    r"""\s*<field\b[^>]*\bname=(['"])is_portal_fee_admin\1[^>]*/>""",
)


def migrate(cr, version):
    cr.execute(
        """
        SELECT id, arch_db
          FROM ir_ui_view
         WHERE arch_db::text LIKE '%is_portal_fee_admin%'
        """
    )
    for view_id, arch_db in cr.fetchall():
        if isinstance(arch_db, str):
            arch_db = json.loads(arch_db)
        cleaned = {lang: _FIELD_RE.sub("", arch) for lang, arch in arch_db.items()}
        cr.execute(
            "UPDATE ir_ui_view SET arch_db = %s::jsonb WHERE id = %s",
            (json.dumps(cleaned), view_id),
        )
