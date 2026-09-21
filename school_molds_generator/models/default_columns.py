# -*- coding: utf-8 -*-
"""First-term mold columns. Sequence is RTL: serial/name on the right, totals on the left."""

# Visual left → right in the Excel:
# المجموع الكلي | المجموع | أعمال السنة | معارف نظرية | مجموع العملي |
# تربية دينية | مبادئ حاسوب | رسم | رياضيات | ميكانيكا | لغة إنجليزية | لغة عربية | الاسم | ر.م
COLOR_ARABIC = '#A8D08D'
COLOR_ENGLISH = '#A8C8E8'
COLOR_MECHANICS = '#FFF3A0'
COLOR_MATH = '#F6E8B8'
COLOR_ART = '#F5E04A'
COLOR_COMPUTER = '#E8A8A8'
COLOR_RELIGION = '#F0A040'
COLOR_PRACTICAL = '#2F5FBF'
COLOR_THEORY = '#F3C4C8'
COLOR_YEAR_WORK = '#E89B8C'
COLOR_TOTAL = '#C43B6E'
COLOR_GRAND = '#C5A01A'

DEFAULT_COLUMNS = [
    {'key': 'serial', 'name': 'ر.م', 'group_name': '', 'col_type': 'serial', 'color': '#F4E04D', 'max_value': 0},
    {'key': 'seat_number', 'name': 'رقم الجلوس', 'group_name': '', 'col_type': 'seat_number', 'color': '#e76f6f', 'max_value': 0},
    {'key': 'pin_number', 'name': 'رقم سري', 'group_name': '', 'col_type': 'pin_number', 'color': '#4957c5', 'max_value': 0},
    {'key': 'name', 'name': 'الاسم', 'group_name': '', 'col_type': 'name', 'color': '#FFFFFF', 'max_value': 0},
    {'key': 'class', 'name': 'الفصل', 'group_name': '', 'col_type': 'class', 'color': '#FFFFFF', 'max_value': 0},
    # Green — لغة عربية (visual LTR: المجموع | أعمال السنة | لغة عربية)
    {'key': 'ar_subject', 'name': 'لغة عربية', 'group_name': 'لغة عربية', 'col_type': 'score', 'color': COLOR_ARABIC, 'max_value': 35},
    {'key': 'ar_work', 'name': 'أعمال السنة', 'group_name': 'لغة عربية', 'col_type': 'score', 'color': COLOR_ARABIC, 'max_value': 15},
    {'key': 'ar_total', 'name': 'المجموع', 'group_name': 'لغة عربية', 'col_type': 'subtotal', 'color': COLOR_ARABIC, 'max_value': 50},
    # Light blue — لغة إنجليزية
    {'key': 'en_subject', 'name': 'لغة إنجليزية', 'group_name': 'لغة إنجليزية', 'col_type': 'score', 'color': COLOR_ENGLISH, 'max_value': 35},
    {'key': 'en_work', 'name': 'أعمال السنة', 'group_name': 'لغة إنجليزية', 'col_type': 'score', 'color': COLOR_ENGLISH, 'max_value': 15},
    {'key': 'en_total', 'name': 'المجموع', 'group_name': 'لغة إنجليزية', 'col_type': 'subtotal', 'color': COLOR_ENGLISH, 'max_value': 50},
    # Light yellow — ميكانيكا
    {'key': 'me_subject', 'name': 'ميكانيكا', 'group_name': 'ميكانيكا', 'col_type': 'score', 'color': COLOR_MECHANICS, 'max_value': 35},
    {'key': 'me_work', 'name': 'أعمال السنة', 'group_name': 'ميكانيكا', 'col_type': 'score', 'color': COLOR_MECHANICS, 'max_value': 15},
    {'key': 'me_total', 'name': 'المجموع', 'group_name': 'ميكانيكا', 'col_type': 'subtotal', 'color': COLOR_MECHANICS, 'max_value': 50},
    # Light cream — رياضيات
    {'key': 'ma_subject', 'name': 'رياضيات', 'group_name': 'رياضيات', 'col_type': 'score', 'color': COLOR_MATH, 'max_value': 35},
    {'key': 'ma_work', 'name': 'أعمال السنة', 'group_name': 'رياضيات', 'col_type': 'score', 'color': COLOR_MATH, 'max_value': 15},
    {'key': 'ma_total', 'name': 'المجموع', 'group_name': 'رياضيات', 'col_type': 'subtotal', 'color': COLOR_MATH, 'max_value': 50},
    # Yellow — رسم / محادثة
    {'key': 'art_draw', 'name': 'رسم', 'group_name': 'رسم', 'col_type': 'score', 'color': COLOR_ART, 'max_value': 25},
    {'key': 'art_talk', 'name': 'محادثة', 'group_name': 'رسم', 'col_type': 'score', 'color': COLOR_ART, 'max_value': 10},
    {'key': 'art_work', 'name': 'أعمال السنة', 'group_name': 'رسم', 'col_type': 'score', 'color': COLOR_ART, 'max_value': 15},
    {'key': 'art_total', 'name': 'المجموع', 'group_name': 'رسم', 'col_type': 'subtotal', 'color': COLOR_ART, 'max_value': 50},
    # Salmon — مبادئ حاسوب / أوفيس
    {'key': 'it_computer', 'name': 'مبادئ حاسوب', 'group_name': 'مبادئ حاسوب', 'col_type': 'score', 'color': COLOR_COMPUTER, 'max_value': 25},
    {'key': 'it_office', 'name': 'أوفيس', 'group_name': 'مبادئ حاسوب', 'col_type': 'score', 'color': COLOR_COMPUTER, 'max_value': 10},
    {'key': 'it_work', 'name': 'أعمال السنة', 'group_name': 'مبادئ حاسوب', 'col_type': 'score', 'color': COLOR_COMPUTER, 'max_value': 15},
    {'key': 'it_total', 'name': 'المجموع', 'group_name': 'مبادئ حاسوب', 'col_type': 'subtotal', 'color': COLOR_COMPUTER, 'max_value': 50},
    # Orange — تربية دينية
    {'key': 're_subject', 'name': 'تربية دينية', 'group_name': 'تربية دينية', 'col_type': 'score', 'color': COLOR_RELIGION, 'max_value': 35},
    {'key': 're_work', 'name': 'أعمال السنة', 'group_name': 'تربية دينية', 'col_type': 'score', 'color': COLOR_RELIGION, 'max_value': 15},
    {'key': 're_total', 'name': 'المجموع', 'group_name': 'تربية دينية', 'col_type': 'subtotal', 'color': COLOR_RELIGION, 'max_value': 50},
    # Left summary columns
    {'key': 'practical_total', 'name': 'مجموع العملي', 'group_name': '', 'col_type': 'score', 'color': COLOR_PRACTICAL, 'max_value': 100},
    {'key': 'theory', 'name': 'معارف نظرية', 'group_name': '', 'col_type': 'score', 'color': COLOR_THEORY, 'max_value': 80},
    {'key': 'year_work', 'name': 'أعمال السنة', 'group_name': '', 'col_type': 'score', 'color': COLOR_YEAR_WORK, 'max_value': 120},
    {'key': 'total', 'name': 'المجموع', 'group_name': '', 'col_type': 'total', 'color': COLOR_TOTAL, 'max_value': 300},
    {'key': 'grand_total', 'name': 'المجموع الكلي', 'group_name': '', 'col_type': 'grand_total', 'color': COLOR_GRAND, 'max_value': 650},
]

# Left summary scores that feed المجموع: مجموع العملي + معارف نظرية + أعمال السنة
SUMMARY_SCORE_KEYS = ('practical_total', 'theory', 'year_work')
IDENTITY_COL_TYPES = ('serial', 'seat_number', 'pin_number', 'name', 'class')

EMPTY_ROW_COUNT = 25
