# -*- coding: utf-8 -*-
"""Create bus.category and bus_category_id columns before ORM/views load."""


def migrate(cr, version):
    cr.execute("""
        CREATE TABLE IF NOT EXISTS bus_category (
            id SERIAL PRIMARY KEY
        )
    """)
    cr.execute("""
        ALTER TABLE bus_category
            ADD COLUMN IF NOT EXISTS name VARCHAR,
            ADD COLUMN IF NOT EXISTS currency_id INTEGER,
            ADD COLUMN IF NOT EXISTS price NUMERIC,
            ADD COLUMN IF NOT EXISTS active BOOLEAN DEFAULT TRUE,
            ADD COLUMN IF NOT EXISTS create_uid INTEGER,
            ADD COLUMN IF NOT EXISTS create_date TIMESTAMP WITHOUT TIME ZONE,
            ADD COLUMN IF NOT EXISTS write_uid INTEGER,
            ADD COLUMN IF NOT EXISTS write_date TIMESTAMP WITHOUT TIME ZONE
    """)

    for table, column in (
        ('res_partner', 'bus_category_id'),
        ('student_fee_plan', 'bus_category_id'),
    ):
        cr.execute("""
            SELECT 1
              FROM information_schema.columns
             WHERE table_name = %s
               AND column_name = %s
        """, (table, column))
        if cr.fetchone():
            continue
        cr.execute(
            "ALTER TABLE %s ADD COLUMN %s INTEGER" % (table, column)
        )
        cr.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                     WHERE conname = '%(table)s_%(column)s_fkey'
                ) THEN
                    ALTER TABLE %(table)s
                        ADD CONSTRAINT %(table)s_%(column)s_fkey
                        FOREIGN KEY (%(column)s)
                        REFERENCES bus_category(id)
                        ON DELETE SET NULL;
                END IF;
            END $$;
        """ % {'table': table, 'column': column})
