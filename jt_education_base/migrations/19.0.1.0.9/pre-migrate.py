# -*- coding: utf-8 -*-
"""Ensure student.class + res.partner.class_id exist before ORM/views load.

Run via module upgrade on production:
  odoo -d <db> -u jt_education_base --stop-after-init
"""


def migrate(cr, version):
    # Table for the new model (ORM will also sync mail mixin columns on upgrade)
    cr.execute("""
        CREATE TABLE IF NOT EXISTS student_class (
            id SERIAL PRIMARY KEY
        )
    """)
    cr.execute("""
        ALTER TABLE student_class
            ADD COLUMN IF NOT EXISTS name VARCHAR,
            ADD COLUMN IF NOT EXISTS create_uid INTEGER,
            ADD COLUMN IF NOT EXISTS create_date TIMESTAMP WITHOUT TIME ZONE,
            ADD COLUMN IF NOT EXISTS write_uid INTEGER,
            ADD COLUMN IF NOT EXISTS write_date TIMESTAMP WITHOUT TIME ZONE
    """)

    # Many2one on res.partner used by student form / partner reads
    cr.execute("""
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = 'res_partner'
           AND column_name = 'class_id'
    """)
    if cr.fetchone():
        return

    cr.execute("""
        ALTER TABLE res_partner
            ADD COLUMN class_id INTEGER
    """)
    cr.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                 WHERE conname = 'res_partner_class_id_fkey'
            ) THEN
                ALTER TABLE res_partner
                    ADD CONSTRAINT res_partner_class_id_fkey
                    FOREIGN KEY (class_id)
                    REFERENCES student_class(id)
                    ON DELETE SET NULL;
            END IF;
        END $$;
    """)
