# -*- coding: utf-8 -*-
from .models.fee_accounting_mixin import CONFIG_KEYS, PRODUCT_XMLIDS


def post_init_hook(env):
    """Set default fee products in system parameters if empty."""
    ICP = env['ir.config_parameter'].sudo()
    for category, key in CONFIG_KEYS.items():
        if ICP.get_param(key):
            continue
        product = env.ref(PRODUCT_XMLIDS[category], raise_if_not_found=False)
        if product:
            ICP.set_param(key, product.id)
