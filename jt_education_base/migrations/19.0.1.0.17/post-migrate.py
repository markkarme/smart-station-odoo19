# -*- coding: utf-8 -*-
"""Make education sequences shared across all companies.

ir.sequence defaults company_id to the company that installed the module,
so next_by_code() returns nothing when working in another company.
"""


def migrate(cr, version):
    cr.execute("""
        UPDATE ir_sequence
           SET company_id = NULL
         WHERE code IN (
            'studentinformation.seq',
            'faculty.seq',
            'parent.seq',
            'roll.no.seq',
            'admissioninformation.seq',
            'studentmeetings.seq'
         )
    """)
