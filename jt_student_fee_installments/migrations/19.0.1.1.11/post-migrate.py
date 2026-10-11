# -*- coding: utf-8 -*-


def migrate(cr, version):
    """Recompute basic labels: #1=المقدم, then القسط 1, 2, ..."""
    cr.execute("""
        UPDATE student_fee_installment
           SET name = 'المقدم - مصاريف دراسية'
         WHERE fee_type = 'basic'
           AND number = 1
    """)
    cr.execute("""
        UPDATE student_fee_installment
           SET name = 'القسط ' || (number - 1) || ' — مصاريف الدراسية'
         WHERE fee_type = 'basic'
           AND number > 1
    """)
    cr.execute("""
        UPDATE student_fee_installment
           SET name = 'القسط ' || number || ' — باصات'
         WHERE fee_type = 'bus'
    """)
