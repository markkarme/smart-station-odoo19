# -*- coding: utf-8 -*-


def post_init_hook(env):
    env['account.journal']._smart_station_configure_paid_journals()
