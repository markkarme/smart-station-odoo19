# -*- coding: utf-8 -*-
"""Load Arabic translations over existing production terms."""

import logging

_logger = logging.getLogger(__name__)

MODULE_NAME = 'jt_education_l10n_ar'
# Official Odoo 19 Arabic is ar_001 (iso_code ar). Variants such as ar_SY
# are also picked up if they are already installed.
OFFICIAL_ARABIC = 'ar_001'


def _arabic_lang_codes(env):
    Lang = env['res.lang'].sudo()
    official = Lang.with_context(active_test=False).search(
        [('code', '=', OFFICIAL_ARABIC)],
        limit=1,
    )
    if official and not official.active:
        official.active = True
        _logger.info('Activated Arabic language %s', OFFICIAL_ARABIC)

    installed = Lang.search([
        '|',
        ('code', '=like', 'ar%'),
        ('iso_code', '=like', 'ar%'),
    ])
    return list(dict.fromkeys(installed.mapped('code')))


def load_arabic_translations(env):
    """Force-import this pack so it replaces older education terms."""
    langs = _arabic_lang_codes(env)
    if not langs:
        _logger.warning(
            'No Arabic language is available; skip loading %s',
            MODULE_NAME,
        )
        return
    _logger.info('Loading %s translations for %s', MODULE_NAME, langs)
    env['ir.module.module']._load_module_terms(
        [MODULE_NAME],
        langs,
        overwrite=True,
    )


def post_init_hook(env):
    load_arabic_translations(env)
