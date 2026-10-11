# -*- coding: utf-8 -*-
"""Ensure product_id exists on student.fee.other before views load."""


def migrate(cr, version):
    cr.execute("""
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = 'student_fee_other'
           AND column_name = 'product_id'
    """)
    if cr.fetchone():
        return

    cr.execute("""
        ALTER TABLE student_fee_other
            ADD COLUMN product_id INTEGER
    """)
    cr.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                 WHERE conname = 'student_fee_other_product_id_fkey'
            ) THEN
                ALTER TABLE student_fee_other
                    ADD CONSTRAINT student_fee_other_product_id_fkey
                    FOREIGN KEY (product_id)
                    REFERENCES product_product(id)
                    ON DELETE SET NULL;
            END IF;
        END $$;
    """)
