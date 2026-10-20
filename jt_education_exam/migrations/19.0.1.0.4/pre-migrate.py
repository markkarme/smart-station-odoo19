# -*- coding: utf-8 -*-


def migrate(cr, version):
    """Add and fill company_id before Odoo applies the required constraint."""
    cr.execute("""
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = 'student_exam'
           AND column_name = 'company_id'
    """)
    if not cr.fetchone():
        cr.execute("ALTER TABLE student_exam ADD COLUMN company_id INTEGER")
    cr.execute("""
        UPDATE student_exam
           SET company_id = (
               SELECT id FROM res_company ORDER BY id LIMIT 1
           )
         WHERE company_id IS NULL
    """)
