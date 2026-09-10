# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Reload pack translations when this module is upgraded."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    from odoo.addons.jt_education_l10n_ar.hooks import load_arabic_translations
    load_arabic_translations(env)
