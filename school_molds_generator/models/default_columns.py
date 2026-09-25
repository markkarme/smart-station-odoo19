# -*- coding: utf-8 -*-
"""Mold column layouts. Sequence is RTL: identity on the right, totals on the left."""

COLOR_ARABIC = '#A8D08D'
COLOR_ENGLISH = '#A8C8E8'
COLOR_MECHANICS = '#FFF3A0'
COLOR_MATH = '#F6E8B8'
COLOR_ART = '#F5E04A'
COLOR_COMPUTER = '#E8A8A8'
COLOR_GRAPHICS = '#B8A0D8'
COLOR_PROGRAMMING = '#7EC8C8'
COLOR_AI = '#D0A8E8'
COLOR_RELIGION = '#F0A040'
COLOR_CIRCUITS = '#E07070'
COLOR_QUALITY = '#F0A8C0'
COLOR_ENTREPRENEUR = '#F5D060'
COLOR_PRACTICAL = '#2F5FBF'
COLOR_THEORY = '#F3C4C8'
COLOR_YEAR_WORK = '#E89B8C'
COLOR_TOTAL = '#C43B6E'
COLOR_GRAND = '#C5A01A'
COLOR_SUMMARY = '#90C090'

# ---------------------------------------------------------------------------
# First term (default for all first-term specializations until split further)
# ---------------------------------------------------------------------------
# Visual left → right:
# المجموع الكلي | المجموع | أعمال السنة | معارف نظرية | مجموع العملي |
# تربية دينية | ذكاء | برمجة | جرافيك | مبادئ حاسوب | رسم | رياضيات | ميكانيكا | لغة إنجليزية | لغة عربية | الاسم | ر.م
FIRST_TERM_COLUMNS = [
    {'key': 'serial', 'name': 'ر.م', 'group_name': '', 'col_type': 'serial', 'color': '#F4E04D', 'max_value': 0},
    {'key': 'seat_number', 'name': 'رقم الجلوس', 'group_name': '', 'col_type': 'seat_number', 'color': '#e76f6f', 'max_value': 0},
    {'key': 'pin_number', 'name': 'رقم سري', 'group_name': '', 'col_type': 'pin_number', 'color': '#4957c5', 'max_value': 0},
    {'key': 'name', 'name': 'الاسم', 'group_name': '', 'col_type': 'name', 'color': '#FFFFFF', 'max_value': 0},
    {'key': 'class', 'name': 'الفصل', 'group_name': '', 'col_type': 'class', 'color': '#FFFFFF', 'max_value': 0},
    {'key': 'ar_subject', 'name': 'لغة عربية', 'group_name': 'لغة عربية', 'col_type': 'score', 'color': COLOR_ARABIC, 'max_value': 35},
    {'key': 'ar_work', 'name': 'أعمال السنة', 'group_name': 'لغة عربية', 'col_type': 'score', 'color': COLOR_ARABIC, 'max_value': 15},
    {'key': 'ar_total', 'name': 'المجموع', 'group_name': 'لغة عربية', 'col_type': 'subtotal', 'color': COLOR_ARABIC, 'max_value': 50},
    {'key': 'en_subject', 'name': 'لغة إنجليزية', 'group_name': 'لغة إنجليزية', 'col_type': 'score', 'color': COLOR_ENGLISH, 'max_value': 35},
    {'key': 'en_work', 'name': 'أعمال السنة', 'group_name': 'لغة إنجليزية', 'col_type': 'score', 'color': COLOR_ENGLISH, 'max_value': 15},
    {'key': 'en_total', 'name': 'المجموع', 'group_name': 'لغة إنجليزية', 'col_type': 'subtotal', 'color': COLOR_ENGLISH, 'max_value': 50},
    {'key': 'me_subject', 'name': 'ميكانيكا', 'group_name': 'ميكانيكا', 'col_type': 'score', 'color': COLOR_MECHANICS, 'max_value': 35},
    {'key': 'me_work', 'name': 'أعمال السنة', 'group_name': 'ميكانيكا', 'col_type': 'score', 'color': COLOR_MECHANICS, 'max_value': 15},
    {'key': 'me_total', 'name': 'المجموع', 'group_name': 'ميكانيكا', 'col_type': 'subtotal', 'color': COLOR_MECHANICS, 'max_value': 50},
    {'key': 'ma_subject', 'name': 'رياضيات', 'group_name': 'رياضيات', 'col_type': 'score', 'color': COLOR_MATH, 'max_value': 35},
    {'key': 'ma_work', 'name': 'أعمال السنة', 'group_name': 'رياضيات', 'col_type': 'score', 'color': COLOR_MATH, 'max_value': 15},
    {'key': 'ma_total', 'name': 'المجموع', 'group_name': 'رياضيات', 'col_type': 'subtotal', 'color': COLOR_MATH, 'max_value': 50},
    {'key': 'art_draw', 'name': 'رسم', 'group_name': 'رسم', 'col_type': 'score', 'color': COLOR_ART, 'max_value': 25},
    {'key': 'art_talk', 'name': 'محادثة', 'group_name': 'رسم', 'col_type': 'score', 'color': COLOR_ART, 'max_value': 10},
    {'key': 'art_work', 'name': 'أعمال السنة', 'group_name': 'رسم', 'col_type': 'score', 'color': COLOR_ART, 'max_value': 15},
    {'key': 'art_total', 'name': 'المجموع', 'group_name': 'رسم', 'col_type': 'subtotal', 'color': COLOR_ART, 'max_value': 50},
    {'key': 'it_computer', 'name': 'مبادئ حاسوب', 'group_name': 'مبادئ حاسوب', 'col_type': 'score', 'color': COLOR_COMPUTER, 'max_value': 25},
    {'key': 'it_office', 'name': 'أوفيس', 'group_name': 'مبادئ حاسوب', 'col_type': 'score', 'color': COLOR_COMPUTER, 'max_value': 10},
    {'key': 'it_work', 'name': 'أعمال السنة', 'group_name': 'مبادئ حاسوب', 'col_type': 'score', 'color': COLOR_COMPUTER, 'max_value': 15},
    {'key': 'it_total', 'name': 'المجموع', 'group_name': 'مبادئ حاسوب', 'col_type': 'subtotal', 'color': COLOR_COMPUTER, 'max_value': 50},
    {'key': 'gr_subject', 'name': 'جرافيك', 'group_name': 'جرافيك', 'col_type': 'score', 'color': COLOR_GRAPHICS, 'max_value': 35},
    {'key': 'gr_work', 'name': 'أعمال السنة', 'group_name': 'جرافيك', 'col_type': 'score', 'color': COLOR_GRAPHICS, 'max_value': 15},
    {'key': 'gr_total', 'name': 'المجموع', 'group_name': 'جرافيك', 'col_type': 'subtotal', 'color': COLOR_GRAPHICS, 'max_value': 50},
    {'key': 'pr_subject', 'name': 'برمجة', 'group_name': 'برمجة', 'col_type': 'score', 'color': COLOR_PROGRAMMING, 'max_value': 35},
    {'key': 'pr_work', 'name': 'أعمال السنة', 'group_name': 'برمجة', 'col_type': 'score', 'color': COLOR_PROGRAMMING, 'max_value': 15},
    {'key': 'pr_total', 'name': 'المجموع', 'group_name': 'برمجة', 'col_type': 'subtotal', 'color': COLOR_PROGRAMMING, 'max_value': 50},
    {'key': 'ai_subject', 'name': 'ذكاء', 'group_name': 'ذكاء', 'col_type': 'score', 'color': COLOR_AI, 'max_value': 35},
    {'key': 'ai_work', 'name': 'أعمال السنة', 'group_name': 'ذكاء', 'col_type': 'score', 'color': COLOR_AI, 'max_value': 15},
    {'key': 'ai_total', 'name': 'المجموع', 'group_name': 'ذكاء', 'col_type': 'subtotal', 'color': COLOR_AI, 'max_value': 50},
    {'key': 're_subject', 'name': 'تربية دينية', 'group_name': 'تربية دينية', 'col_type': 'score', 'color': COLOR_RELIGION, 'max_value': 35, 'include_in_grand_total': False},
    {'key': 're_work', 'name': 'أعمال السنة', 'group_name': 'تربية دينية', 'col_type': 'score', 'color': COLOR_RELIGION, 'max_value': 15, 'include_in_grand_total': False},
    {'key': 're_total', 'name': 'المجموع', 'group_name': 'تربية دينية', 'col_type': 'subtotal', 'color': COLOR_RELIGION, 'max_value': 50, 'include_in_grand_total': False},
    {'key': 'practical_total', 'name': 'مجموع العملي', 'group_name': '', 'col_type': 'score', 'color': COLOR_PRACTICAL, 'max_value': 100},
    {'key': 'theory', 'name': 'معارف نظرية', 'group_name': '', 'col_type': 'score', 'color': COLOR_THEORY, 'max_value': 80},
    {'key': 'year_work', 'name': 'أعمال السنة', 'group_name': '', 'col_type': 'score', 'color': COLOR_YEAR_WORK, 'max_value': 120},
    {'key': 'total', 'name': 'المجموع', 'group_name': '', 'col_type': 'total', 'color': COLOR_TOTAL, 'max_value': 300},
    {'key': 'grand_total', 'name': 'المجموع الكلي', 'group_name': '', 'col_type': 'grand_total', 'color': COLOR_GRAND, 'max_value': 750},
]

# ---------------------------------------------------------------------------
# Second term — الكترونيات صناعية
# ---------------------------------------------------------------------------
# Visual left → right from screenshot:
# المجموع 550 | المجموع 300 | اعمال السنة 120 | مجموع العملي 100 | معارف نظرية 80 |
# ريادة اعمال | مراقبة جودة | رسم الدوائر الالكترونية | رياضيات | ميكانيكا | لغة إنجليزية | لغة عربية | الفصل | الاسم | رقم سري | رقم الجلوس | م
# مراقبة جودة + ريادة اعمال are shown but NOT in المجموع الكلي (5×50 + 300 = 550)
SECOND_TERM_INDUSTRIAL_ELECTRONICS_COLUMNS = [
    {'key': 'serial', 'name': 'م', 'group_name': '', 'col_type': 'serial', 'color': '#F4E04D', 'max_value': 0},
    {'key': 'seat_number', 'name': 'رقم الجلوس', 'group_name': '', 'col_type': 'seat_number', 'color': '#e76f6f', 'max_value': 0},
    {'key': 'pin_number', 'name': 'الرقم السري', 'group_name': '', 'col_type': 'pin_number', 'color': '#4957c5', 'max_value': 0},
    {'key': 'name', 'name': 'الاسم', 'group_name': '', 'col_type': 'name', 'color': '#F5C080', 'max_value': 0},
    {'key': 'class', 'name': 'الفصل', 'group_name': '', 'col_type': 'class', 'color': '#F5C080', 'max_value': 0},
    # لغة عربية
    {'key': 'ar_subject', 'name': 'لغة عربية', 'group_name': 'لغة عربية', 'col_type': 'score', 'color': '#E8C060', 'max_value': 35},
    {'key': 'ar_work', 'name': 'أعمال السنة', 'group_name': 'لغة عربية', 'col_type': 'score', 'color': '#E8C060', 'max_value': 15},
    {'key': 'ar_total', 'name': 'المجموع', 'group_name': 'لغة عربية', 'col_type': 'subtotal', 'color': '#E8C060', 'max_value': 50},
    # لغة إنجليزية
    {'key': 'en_subject', 'name': 'لغة إنجليزية', 'group_name': 'لغة إنجليزية', 'col_type': 'score', 'color': '#E8A0B8', 'max_value': 35},
    {'key': 'en_work', 'name': 'أعمال السنة', 'group_name': 'لغة إنجليزية', 'col_type': 'score', 'color': '#E8A0B8', 'max_value': 15},
    {'key': 'en_total', 'name': 'المجموع', 'group_name': 'لغة إنجليزية', 'col_type': 'subtotal', 'color': '#E8A0B8', 'max_value': 50},
    # ميكانيكا
    {'key': 'me_subject', 'name': 'ميكانيكا', 'group_name': 'ميكانيكا', 'col_type': 'score', 'color': '#A8C0D8', 'max_value': 35},
    {'key': 'me_work', 'name': 'أعمال السنة', 'group_name': 'ميكانيكا', 'col_type': 'score', 'color': '#A8C0D8', 'max_value': 15},
    {'key': 'me_total', 'name': 'المجموع', 'group_name': 'ميكانيكا', 'col_type': 'subtotal', 'color': '#A8C0D8', 'max_value': 50},
    # رياضيات
    {'key': 'ma_subject', 'name': 'رياضيات', 'group_name': 'رياضيات', 'col_type': 'score', 'color': '#A8D080', 'max_value': 35},
    {'key': 'ma_work', 'name': 'أعمال السنة', 'group_name': 'رياضيات', 'col_type': 'score', 'color': '#A8D080', 'max_value': 15},
    {'key': 'ma_total', 'name': 'المجموع', 'group_name': 'رياضيات', 'col_type': 'subtotal', 'color': '#A8D080', 'max_value': 50},
    # رسم الدوائر الالكترونية
    {'key': 'ec_subject', 'name': 'رسم الدوائر الالكترونية', 'group_name': 'رسم الدوائر الالكترونية', 'col_type': 'score', 'color': COLOR_CIRCUITS, 'max_value': 35},
    {'key': 'ec_work', 'name': 'أعمال السنة', 'group_name': 'رسم الدوائر الالكترونية', 'col_type': 'score', 'color': COLOR_CIRCUITS, 'max_value': 15},
    {'key': 'ec_total', 'name': 'المجموع', 'group_name': 'رسم الدوائر الالكترونية', 'col_type': 'subtotal', 'color': COLOR_CIRCUITS, 'max_value': 50},
    # مراقبة جودة — not in المجموع الكلي
    {'key': 'qc_subject', 'name': 'مراقبة جودة', 'group_name': 'مراقبة جودة', 'col_type': 'score', 'color': COLOR_QUALITY, 'max_value': 35, 'include_in_grand_total': False},
    {'key': 'qc_work', 'name': 'أعمال السنة', 'group_name': 'مراقبة جودة', 'col_type': 'score', 'color': COLOR_QUALITY, 'max_value': 15, 'include_in_grand_total': False},
    {'key': 'qc_total', 'name': 'المجموع', 'group_name': 'مراقبة جودة', 'col_type': 'subtotal', 'color': COLOR_QUALITY, 'max_value': 50, 'include_in_grand_total': False},
    # ريادة اعمال — not in المجموع الكلي
    {'key': 'ent_subject', 'name': 'ريادة اعمال', 'group_name': 'ريادة اعمال', 'col_type': 'score', 'color': COLOR_ENTREPRENEUR, 'max_value': 35, 'include_in_grand_total': False},
    {'key': 'ent_work', 'name': 'أعمال السنة', 'group_name': 'ريادة اعمال', 'col_type': 'score', 'color': COLOR_ENTREPRENEUR, 'max_value': 15, 'include_in_grand_total': False},
    {'key': 'ent_total', 'name': 'المجموع', 'group_name': 'ريادة اعمال', 'col_type': 'subtotal', 'color': COLOR_ENTREPRENEUR, 'max_value': 50, 'include_in_grand_total': False},
    # Summary block (order matches screenshot)
    {'key': 'theory', 'name': 'معارف نظرية', 'group_name': '', 'col_type': 'score', 'color': COLOR_SUMMARY, 'max_value': 80},
    {'key': 'practical_total', 'name': 'مجموع العملي', 'group_name': '', 'col_type': 'score', 'color': COLOR_SUMMARY, 'max_value': 100},
    {'key': 'year_work', 'name': 'اعمال السنة', 'group_name': '', 'col_type': 'score', 'color': COLOR_SUMMARY, 'max_value': 120},
    {'key': 'total', 'name': 'المجموع', 'group_name': '', 'col_type': 'total', 'color': COLOR_SUMMARY, 'max_value': 300},
    # 5 subjects × 50 + summary 300 = 550
    {'key': 'grand_total', 'name': 'المجموع', 'group_name': '', 'col_type': 'grand_total', 'color': '#E89090', 'max_value': 550},
]

# ---------------------------------------------------------------------------
# Second term — كهرباء صناعية
# ---------------------------------------------------------------------------
# Visual left → right from screenshot:
# المجموع الكلي 600 | المجموع 300 | اعمال السنة 120 | العملي 100 | معارف نظرية 80 |
# ريادة اعمال | مراقبة جودة | هندسة كهربائية | رسم فني اوتوميشن | رياضيات | ميكانيكا | لغة إنجليزية | لغة عربية | الفصل | الاسم | رقم سري | رقم الجلوس | م
# مراقبة جودة + ريادة اعمال NOT in المجموع الكلي (6×50 + 300 = 600)
SECOND_TERM_INDUSTRIAL_ELECTRICITY_COLUMNS = [
    {'key': 'serial', 'name': 'م', 'group_name': '', 'col_type': 'serial', 'color': '#F4E04D', 'max_value': 0},
    {'key': 'seat_number', 'name': 'رقم الجلوس', 'group_name': '', 'col_type': 'seat_number', 'color': '#e76f6f', 'max_value': 0},
    {'key': 'pin_number', 'name': 'الرقم السري', 'group_name': '', 'col_type': 'pin_number', 'color': '#4957c5', 'max_value': 0},
    {'key': 'name', 'name': 'الاسم', 'group_name': '', 'col_type': 'name', 'color': '#FFFFFF', 'max_value': 0},
    {'key': 'class', 'name': 'الفصل', 'group_name': '', 'col_type': 'class', 'color': '#F5C080', 'max_value': 0},
    # لغة عربية
    {'key': 'ar_subject', 'name': 'لغة عربية', 'group_name': 'لغة عربية', 'col_type': 'score', 'color': '#E07070', 'max_value': 35},
    {'key': 'ar_work', 'name': 'أعمال السنة', 'group_name': 'لغة عربية', 'col_type': 'score', 'color': '#E07070', 'max_value': 15},
    {'key': 'ar_total', 'name': 'المجموع', 'group_name': 'لغة عربية', 'col_type': 'subtotal', 'color': '#E07070', 'max_value': 50},
    # لغة إنجليزية
    {'key': 'en_subject', 'name': 'لغة إنجليزية', 'group_name': 'لغة إنجليزية', 'col_type': 'score', 'color': '#D0A0C8', 'max_value': 35},
    {'key': 'en_work', 'name': 'أعمال السنة', 'group_name': 'لغة إنجليزية', 'col_type': 'score', 'color': '#D0A0C8', 'max_value': 15},
    {'key': 'en_total', 'name': 'المجموع', 'group_name': 'لغة إنجليزية', 'col_type': 'subtotal', 'color': '#D0A0C8', 'max_value': 50},
    # ميكانيكا
    {'key': 'me_subject', 'name': 'ميكانيكا', 'group_name': 'ميكانيكا', 'col_type': 'score', 'color': '#90C090', 'max_value': 35},
    {'key': 'me_work', 'name': 'أعمال السنة', 'group_name': 'ميكانيكا', 'col_type': 'score', 'color': '#90C090', 'max_value': 15},
    {'key': 'me_total', 'name': 'المجموع', 'group_name': 'ميكانيكا', 'col_type': 'subtotal', 'color': '#90C090', 'max_value': 50},
    # رياضيات
    {'key': 'ma_subject', 'name': 'رياضيات', 'group_name': 'رياضيات', 'col_type': 'score', 'color': '#F0A060', 'max_value': 35},
    {'key': 'ma_work', 'name': 'أعمال السنة', 'group_name': 'رياضيات', 'col_type': 'score', 'color': '#F0A060', 'max_value': 15},
    {'key': 'ma_total', 'name': 'المجموع', 'group_name': 'رياضيات', 'col_type': 'subtotal', 'color': '#F0A060', 'max_value': 50},
    # رسم فني "اوتوميشن" — 25 + 10 + 15 = 50
    {'key': 'au_draw', 'name': 'رسم فني', 'group_name': 'رسم فني اوتوميشن', 'col_type': 'score', 'color': '#A0C8E8', 'max_value': 25},
    {'key': 'au_auto', 'name': 'اوتوميشن', 'group_name': 'رسم فني اوتوميشن', 'col_type': 'score', 'color': '#A0C8E8', 'max_value': 10},
    {'key': 'au_work', 'name': 'أعمال السنة', 'group_name': 'رسم فني اوتوميشن', 'col_type': 'score', 'color': '#A0C8E8', 'max_value': 15},
    {'key': 'au_total', 'name': 'المجموع', 'group_name': 'رسم فني اوتوميشن', 'col_type': 'subtotal', 'color': '#A0C8E8', 'max_value': 50},
    # هندسة كهربائية
    {'key': 'ee_subject', 'name': 'هندسة كهربائية', 'group_name': 'هندسة كهربائية', 'col_type': 'score', 'color': '#F0E080', 'max_value': 35},
    {'key': 'ee_work', 'name': 'أعمال السنة', 'group_name': 'هندسة كهربائية', 'col_type': 'score', 'color': '#F0E080', 'max_value': 15},
    {'key': 'ee_total', 'name': 'المجموع', 'group_name': 'هندسة كهربائية', 'col_type': 'subtotal', 'color': '#F0E080', 'max_value': 50},
    # مراقبة جودة — not in المجموع الكلي
    {'key': 'qc_subject', 'name': 'مراقبة جودة', 'group_name': 'مراقبة جودة', 'col_type': 'score', 'color': COLOR_QUALITY, 'max_value': 35, 'include_in_grand_total': False},
    {'key': 'qc_work', 'name': 'أعمال السنة', 'group_name': 'مراقبة جودة', 'col_type': 'score', 'color': COLOR_QUALITY, 'max_value': 15, 'include_in_grand_total': False},
    {'key': 'qc_total', 'name': 'المجموع', 'group_name': 'مراقبة جودة', 'col_type': 'subtotal', 'color': COLOR_QUALITY, 'max_value': 50, 'include_in_grand_total': False},
    # ريادة اعمال — not in المجموع الكلي
    {'key': 'ent_subject', 'name': 'ريادة اعمال', 'group_name': 'ريادة اعمال', 'col_type': 'score', 'color': '#7090C8', 'max_value': 35, 'include_in_grand_total': False},
    {'key': 'ent_work', 'name': 'أعمال السنة', 'group_name': 'ريادة اعمال', 'col_type': 'score', 'color': '#7090C8', 'max_value': 15, 'include_in_grand_total': False},
    {'key': 'ent_total', 'name': 'المجموع', 'group_name': 'ريادة اعمال', 'col_type': 'subtotal', 'color': '#7090C8', 'max_value': 50, 'include_in_grand_total': False},
    # Summary block
    {'key': 'theory', 'name': 'معارف نظرية', 'group_name': '', 'col_type': 'score', 'color': '#D0A0C8', 'max_value': 80},
    {'key': 'practical_total', 'name': 'العملي', 'group_name': '', 'col_type': 'score', 'color': '#D0A0C8', 'max_value': 100},
    {'key': 'year_work', 'name': 'اعمال السنة', 'group_name': '', 'col_type': 'score', 'color': '#D0A0C8', 'max_value': 120},
    {'key': 'total', 'name': 'المجموع', 'group_name': '', 'col_type': 'total', 'color': '#D0A0C8', 'max_value': 300},
    # 6 subjects × 50 + summary 300 = 600
    {'key': 'grand_total', 'name': 'المجموع الكلي', 'group_name': '', 'col_type': 'grand_total', 'color': '#E89090', 'max_value': 600},
]

# ---------------------------------------------------------------------------
# Second term — حاسب الي
# ---------------------------------------------------------------------------
# Visual left → right from screenshot:
# المجموع الكلي 500 | المجموع 300 | اعمال السنة 120 | مجموع العملي 100 | معارف نظرية 80 |
# ريادة اعمال | مراقبه جوده | رياضيات | ميكانيكا | لغة إنجليزية | لغة عربية | الفصل | الاسم | رقم سري | رقم الجلوس | م
# مراقبة جودة + ريادة اعمال NOT in المجموع الكلي (4×50 + 300 = 500)
SECOND_TERM_COMPUTER_COLUMNS = [
    {'key': 'serial', 'name': 'م', 'group_name': '', 'col_type': 'serial', 'color': '#F4E04D', 'max_value': 0},
    {'key': 'seat_number', 'name': 'رقم الجلوس', 'group_name': '', 'col_type': 'seat_number', 'color': '#e76f6f', 'max_value': 0},
    {'key': 'pin_number', 'name': 'الرقم السري', 'group_name': '', 'col_type': 'pin_number', 'color': '#4957c5', 'max_value': 0},
    {'key': 'name', 'name': 'الاسم', 'group_name': '', 'col_type': 'name', 'color': '#F5A040', 'max_value': 0},
    {'key': 'class', 'name': 'الفصل', 'group_name': '', 'col_type': 'class', 'color': '#A0C8E8', 'max_value': 0},
    # لغة عربية
    {'key': 'ar_subject', 'name': 'لغة عربية', 'group_name': 'لغة عربية', 'col_type': 'score', 'color': '#90C070', 'max_value': 35},
    {'key': 'ar_work', 'name': 'أعمال السنة', 'group_name': 'لغة عربية', 'col_type': 'score', 'color': '#90C070', 'max_value': 15},
    {'key': 'ar_total', 'name': 'المجموع', 'group_name': 'لغة عربية', 'col_type': 'subtotal', 'color': '#90C070', 'max_value': 50},
    # لغة إنجليزية
    {'key': 'en_subject', 'name': 'لغة إنجليزية', 'group_name': 'لغة إنجليزية', 'col_type': 'score', 'color': '#E8A0B8', 'max_value': 35},
    {'key': 'en_work', 'name': 'أعمال السنة', 'group_name': 'لغة إنجليزية', 'col_type': 'score', 'color': '#E8A0B8', 'max_value': 15},
    {'key': 'en_total', 'name': 'المجموع', 'group_name': 'لغة إنجليزية', 'col_type': 'subtotal', 'color': '#E8A0B8', 'max_value': 50},
    # ميكانيكا
    {'key': 'me_subject', 'name': 'ميكانيكا', 'group_name': 'ميكانيكا', 'col_type': 'score', 'color': '#F0E080', 'max_value': 35},
    {'key': 'me_work', 'name': 'أعمال السنة', 'group_name': 'ميكانيكا', 'col_type': 'score', 'color': '#F0E080', 'max_value': 15},
    {'key': 'me_total', 'name': 'المجموع', 'group_name': 'ميكانيكا', 'col_type': 'subtotal', 'color': '#F0E080', 'max_value': 50},
    # رياضيات
    {'key': 'ma_subject', 'name': 'رياضيات', 'group_name': 'رياضيات', 'col_type': 'score', 'color': '#A0D0E8', 'max_value': 35},
    {'key': 'ma_work', 'name': 'أعمال السنة', 'group_name': 'رياضيات', 'col_type': 'score', 'color': '#A0D0E8', 'max_value': 15},
    {'key': 'ma_total', 'name': 'المجموع', 'group_name': 'رياضيات', 'col_type': 'subtotal', 'color': '#A0D0E8', 'max_value': 50},
    # مراقبة جودة — not in المجموع الكلي
    {'key': 'qc_subject', 'name': 'مراقبة جودة', 'group_name': 'مراقبة جودة', 'col_type': 'score', 'color': '#C090D0', 'max_value': 35, 'include_in_grand_total': False},
    {'key': 'qc_work', 'name': 'أعمال السنة', 'group_name': 'مراقبة جودة', 'col_type': 'score', 'color': '#C090D0', 'max_value': 15, 'include_in_grand_total': False},
    {'key': 'qc_total', 'name': 'المجموع', 'group_name': 'مراقبة جودة', 'col_type': 'subtotal', 'color': '#C090D0', 'max_value': 50, 'include_in_grand_total': False},
    # ريادة اعمال — not in المجموع الكلي
    {'key': 'ent_subject', 'name': 'ريادة اعمال', 'group_name': 'ريادة اعمال', 'col_type': 'score', 'color': '#D0B0E0', 'max_value': 35, 'include_in_grand_total': False},
    {'key': 'ent_work', 'name': 'أعمال السنة', 'group_name': 'ريادة اعمال', 'col_type': 'score', 'color': '#D0B0E0', 'max_value': 15, 'include_in_grand_total': False},
    {'key': 'ent_total', 'name': 'المجموع', 'group_name': 'ريادة اعمال', 'col_type': 'subtotal', 'color': '#D0B0E0', 'max_value': 50, 'include_in_grand_total': False},
    # Summary / العملي block
    {'key': 'theory', 'name': 'معارف نظرية', 'group_name': '', 'col_type': 'score', 'color': '#E890A0', 'max_value': 80},
    {'key': 'practical_total', 'name': 'مجموع العملي', 'group_name': '', 'col_type': 'score', 'color': '#E890A0', 'max_value': 100},
    {'key': 'year_work', 'name': 'اعمال السنة', 'group_name': '', 'col_type': 'score', 'color': '#E890A0', 'max_value': 120},
    {'key': 'total', 'name': 'المجموع', 'group_name': '', 'col_type': 'total', 'color': '#E890A0', 'max_value': 300},
    # 4 subjects × 50 + summary 300 = 500
    {'key': 'grand_total', 'name': 'المجموع الكلي', 'group_name': '', 'col_type': 'grand_total', 'color': '#E8D0A0', 'max_value': 500},
]

# ---------------------------------------------------------------------------
# Second term — اجهزة مكتبية
# ---------------------------------------------------------------------------
# Visual left → right from corrected screenshot:
# المجموع الكلي 600 | المجموع 300 | أعمال سنة 120 | معارف نظرية 80 | مجموع العملي 100 |
# تربية دينية | مبادئ حاسوب | رسم صناعي | رياضيات | ميكانيكا | لغة إنجليزية | لغة عربية | الفصل | الاسم | رقم سري | رقم الجلوس | م
# تربية دينية NOT in المجموع الكلي (6×50 + 300 = 600)
SECOND_TERM_OFFICE_EQUIPMENT_COLUMNS = [
    {'key': 'serial', 'name': 'م', 'group_name': '', 'col_type': 'serial', 'color': '#F4E04D', 'max_value': 0},
    {'key': 'seat_number', 'name': 'رقم الجلوس', 'group_name': '', 'col_type': 'seat_number', 'color': '#e76f6f', 'max_value': 0},
    {'key': 'pin_number', 'name': 'الرقم السري', 'group_name': '', 'col_type': 'pin_number', 'color': '#4957c5', 'max_value': 0},
    {'key': 'name', 'name': 'الاسم', 'group_name': '', 'col_type': 'name', 'color': '#FFFFFF', 'max_value': 0},
    {'key': 'class', 'name': 'الفصل', 'group_name': '', 'col_type': 'class', 'color': '#FFFFFF', 'max_value': 0},
    # لغة عربية
    {'key': 'ar_subject', 'name': 'لغة عربية', 'group_name': 'لغة عربية', 'col_type': 'score', 'color': '#90C070', 'max_value': 35},
    {'key': 'ar_work', 'name': 'أعمال السنة', 'group_name': 'لغة عربية', 'col_type': 'score', 'color': '#90C070', 'max_value': 15},
    {'key': 'ar_total', 'name': 'المجموع', 'group_name': 'لغة عربية', 'col_type': 'subtotal', 'color': '#90C070', 'max_value': 50},
    # لغة إنجليزية
    {'key': 'en_subject', 'name': 'لغة إنجليزية', 'group_name': 'لغة إنجليزية', 'col_type': 'score', 'color': '#A8C8E8', 'max_value': 35},
    {'key': 'en_work', 'name': 'أعمال السنة', 'group_name': 'لغة إنجليزية', 'col_type': 'score', 'color': '#A8C8E8', 'max_value': 15},
    {'key': 'en_total', 'name': 'المجموع', 'group_name': 'لغة إنجليزية', 'col_type': 'subtotal', 'color': '#A8C8E8', 'max_value': 50},
    # ميكانيكا
    {'key': 'me_subject', 'name': 'ميكانيكا', 'group_name': 'ميكانيكا', 'col_type': 'score', 'color': '#F0E080', 'max_value': 35},
    {'key': 'me_work', 'name': 'أعمال السنة', 'group_name': 'ميكانيكا', 'col_type': 'score', 'color': '#F0E080', 'max_value': 15},
    {'key': 'me_total', 'name': 'المجموع', 'group_name': 'ميكانيكا', 'col_type': 'subtotal', 'color': '#F0E080', 'max_value': 50},
    # رياضيات
    {'key': 'ma_subject', 'name': 'رياضيات', 'group_name': 'رياضيات', 'col_type': 'score', 'color': '#F0D0B0', 'max_value': 35},
    {'key': 'ma_work', 'name': 'أعمال السنة', 'group_name': 'رياضيات', 'col_type': 'score', 'color': '#F0D0B0', 'max_value': 15},
    {'key': 'ma_total', 'name': 'المجموع', 'group_name': 'رياضيات', 'col_type': 'subtotal', 'color': '#F0D0B0', 'max_value': 50},
    # رسم صناعي — 25 + 10 + 15 = 50
    {'key': 'id_equations', 'name': 'رسم معادلات', 'group_name': 'رسم صناعي', 'col_type': 'score', 'color': '#F5E04A', 'max_value': 25},
    {'key': 'id_extra', 'name': 'تطبيق', 'group_name': 'رسم صناعي', 'col_type': 'score', 'color': '#F5E04A', 'max_value': 10},
    {'key': 'id_work', 'name': 'أعمال السنة', 'group_name': 'رسم صناعي', 'col_type': 'score', 'color': '#F5E04A', 'max_value': 15},
    {'key': 'id_total', 'name': 'المجموع', 'group_name': 'رسم صناعي', 'col_type': 'subtotal', 'color': '#F5E04A', 'max_value': 50},
    # مبادئ حاسوب آلي — 25 + 10 + 15 = 50
    {'key': 'it_computer', 'name': 'مبادئ حاسوب', 'group_name': 'مبادئ حاسوب آلي', 'col_type': 'score', 'color': '#E89090', 'max_value': 25},
    {'key': 'it_office', 'name': 'أوفيس', 'group_name': 'مبادئ حاسوب آلي', 'col_type': 'score', 'color': '#E89090', 'max_value': 10},
    {'key': 'it_work', 'name': 'أعمال السنة', 'group_name': 'مبادئ حاسوب آلي', 'col_type': 'score', 'color': '#E89090', 'max_value': 15},
    {'key': 'it_total', 'name': 'المجموع', 'group_name': 'مبادئ حاسوب آلي', 'col_type': 'subtotal', 'color': '#E89090', 'max_value': 50},
    # تربية دينية — not in المجموع الكلي
    {'key': 're_subject', 'name': 'تربية دينية', 'group_name': 'تربية دينية', 'col_type': 'score', 'color': COLOR_RELIGION, 'max_value': 35, 'include_in_grand_total': False},
    {'key': 're_work', 'name': 'أعمال السنة', 'group_name': 'تربية دينية', 'col_type': 'score', 'color': COLOR_RELIGION, 'max_value': 15, 'include_in_grand_total': False},
    {'key': 're_total', 'name': 'المجموع', 'group_name': 'تربية دينية', 'col_type': 'subtotal', 'color': COLOR_RELIGION, 'max_value': 50, 'include_in_grand_total': False},
    # Summary (order matches screenshot)
    {'key': 'practical_total', 'name': 'مجموع العملي', 'group_name': '', 'col_type': 'score', 'color': '#2F5FBF', 'max_value': 100},
    {'key': 'theory', 'name': 'معارف نظرية', 'group_name': '', 'col_type': 'score', 'color': '#D0A0C8', 'max_value': 80},
    {'key': 'year_work', 'name': 'أعمال سنة', 'group_name': '', 'col_type': 'score', 'color': '#E8A090', 'max_value': 120},
    {'key': 'total', 'name': 'المجموع', 'group_name': '', 'col_type': 'total', 'color': '#C090D0', 'max_value': 300},
    # 6 subjects × 50 + summary 300 = 600
    {'key': 'grand_total', 'name': 'المجموع الكلي', 'group_name': '', 'col_type': 'grand_total', 'color': '#C5A01A', 'max_value': 600},
]

# Backwards-compatible alias
DEFAULT_COLUMNS = FIRST_TERM_COLUMNS

SUMMARY_SCORE_KEYS = ('practical_total', 'theory', 'year_work')
IDENTITY_COL_TYPES = ('serial', 'seat_number', 'pin_number', 'name', 'class')
EMPTY_ROW_COUNT = 25
HEALTH_INSURANCE_ROW_COUNT = 35
FORM_27_ROW_COUNT = 40

# ---------------------------------------------------------------------------
# Third term — حاسب الي
# ---------------------------------------------------------------------------
# Visual left → right from screenshot:
# المجموع 500 | العملي 200 | صيانة الآلات 100 | لغة انجليزية 50 | ميكانيكا 50 | تكنولوجيا 100 | الفصل | الاسم | رقم الجلوس/سري | م
# Single-score columns (no 35/15 split); all included in المجموع (100+50+50+100+200 = 500)
THIRD_TERM_COMPUTER_COLUMNS = [
    {'key': 'serial', 'name': 'م', 'group_name': '', 'col_type': 'serial', 'color': '#6FA8DC', 'max_value': 0},
    {'key': 'seat_number', 'name': 'رقم الجلوس / الرقم السري', 'group_name': '', 'col_type': 'seat_number', 'color': '#FFFFFF', 'max_value': 0},
    {'key': 'name', 'name': 'الاسم', 'group_name': '', 'col_type': 'name', 'color': '#B6D7A8', 'max_value': 0},
    {'key': 'class', 'name': 'الفصل', 'group_name': '', 'col_type': 'class', 'color': '#B6D7A8', 'max_value': 0},
    {'key': 'technology', 'name': 'تكنولوجيا', 'group_name': '', 'col_type': 'score', 'color': '#B6D7A8', 'max_value': 100},
    {'key': 'mechanics', 'name': 'ميكانيكا', 'group_name': '', 'col_type': 'score', 'color': '#F9CB9C', 'max_value': 50},
    {'key': 'english', 'name': 'لغة انجليزية', 'group_name': '', 'col_type': 'score', 'color': '#CC4125', 'max_value': 50},
    {'key': 'machine_maint', 'name': 'صيانة الآلات', 'group_name': '', 'col_type': 'score', 'color': '#FFE599', 'max_value': 100},
    {'key': 'practical', 'name': 'العملي', 'group_name': '', 'col_type': 'score', 'color': '#B45F06', 'max_value': 200},
    {'key': 'total', 'name': 'المجموع', 'group_name': '', 'col_type': 'total', 'color': '#FFFFFF', 'max_value': 500},
]

# ---------------------------------------------------------------------------
# Third term — الكترونيات صناعية
# ---------------------------------------------------------------------------
# Visual left → right from screenshot:
# المجموع 500 | العملي 200 | رسم دوائر الكترونية 100 | لغة انجليزية 50 | ميكانيكا 50 |
# تكنولوجيا المقايسات 100 | الفصل | الاسم | الرقم السري | رقم الجلوس | م
# All included: 100+50+50+100+200 = 500
THIRD_TERM_INDUSTRIAL_ELECTRONICS_COLUMNS = [
    {'key': 'serial', 'name': 'م', 'group_name': '', 'col_type': 'serial', 'color': '#F4E04D', 'max_value': 0},
    {'key': 'seat_number', 'name': 'رقم الجلوس', 'group_name': '', 'col_type': 'seat_number', 'color': '#FFFFFF', 'max_value': 0},
    {'key': 'pin_number', 'name': 'الرقم السري', 'group_name': '', 'col_type': 'pin_number', 'color': '#FFFFFF', 'max_value': 0},
    {'key': 'name', 'name': 'الاسم', 'group_name': '', 'col_type': 'name', 'color': '#F5C080', 'max_value': 0},
    {'key': 'class', 'name': 'الفصل', 'group_name': '', 'col_type': 'class', 'color': '#F5C080', 'max_value': 0},
    {'key': 'meas_tech', 'name': 'تكنولوجيا المقايسات', 'group_name': '', 'col_type': 'score', 'color': '#B6D7A8', 'max_value': 100},
    {'key': 'mechanics', 'name': 'ميكانيكا', 'group_name': '', 'col_type': 'score', 'color': '#F9CB9C', 'max_value': 50},
    {'key': 'english', 'name': 'لغة انجليزية', 'group_name': '', 'col_type': 'score', 'color': '#CC4125', 'max_value': 50},
    {'key': 'circuit_draw', 'name': 'رسم دوائر الكترونية', 'group_name': '', 'col_type': 'score', 'color': '#FFE599', 'max_value': 100},
    {'key': 'practical', 'name': 'العملي', 'group_name': '', 'col_type': 'score', 'color': '#B45F06', 'max_value': 200},
    {'key': 'total', 'name': 'المجموع', 'group_name': '', 'col_type': 'total', 'color': '#FFFFFF', 'max_value': 500},
]

# ---------------------------------------------------------------------------
# Third term — كهرباء صناعية
# ---------------------------------------------------------------------------
# Visual left → right from screenshot:
# المجموع 500 | العملي 200 | مجموع الرسم 100 | رسم فني كهرباء 70 | autocad 30 |
# لغة انجليزية 50 | ميكانيكا 50 | تكنولوجيا الحاسب 100 | الفصل | الاسم | الرقم السري | رقم الجلوس | م
# Drawing group: autocad 30 + رسم فني كهرباء 70 = مجموع الرسم 100
# Total: 100+50+50+100+200 = 500
THIRD_TERM_INDUSTRIAL_ELECTRICITY_COLUMNS = [
    {'key': 'serial', 'name': 'م', 'group_name': '', 'col_type': 'serial', 'color': '#6FA8DC', 'max_value': 0},
    {'key': 'seat_number', 'name': 'رقم الجلوس', 'group_name': '', 'col_type': 'seat_number', 'color': '#F5C080', 'max_value': 0},
    {'key': 'pin_number', 'name': 'الرقم السري', 'group_name': '', 'col_type': 'pin_number', 'color': '#F5C080', 'max_value': 0},
    {'key': 'name', 'name': 'الاسم', 'group_name': '', 'col_type': 'name', 'color': '#F5C080', 'max_value': 0},
    {'key': 'class', 'name': 'الفصل', 'group_name': '', 'col_type': 'class', 'color': '#F5C080', 'max_value': 0},
    {'key': 'comp_tech', 'name': ' تكنولوجيا المقايسات ', 'group_name': '', 'col_type': 'score', 'color': '#B6D7A8', 'max_value': 100},
    {'key': 'mechanics', 'name': 'ميكانيكا', 'group_name': '', 'col_type': 'score', 'color': '#F9CB9C', 'max_value': 50},
    {'key': 'english', 'name': 'لغة انجليزية', 'group_name': '', 'col_type': 'score', 'color': '#CC4125', 'max_value': 50},
    {'key': 'autocad', 'name': 'autocad', 'group_name': 'مجموع الرسم', 'col_type': 'score', 'color': '#FFE599', 'max_value': 30},
    {'key': 'elec_draw', 'name': 'رسم فني كهرباء', 'group_name': 'مجموع الرسم', 'col_type': 'score', 'color': '#FFE599', 'max_value': 70},
    {'key': 'drawing_total', 'name': 'مجموع الرسم', 'group_name': 'مجموع الرسم', 'col_type': 'subtotal', 'color': '#FFE599', 'max_value': 100},
    {'key': 'practical', 'name': 'العملي', 'group_name': '', 'col_type': 'score', 'color': '#B45F06', 'max_value': 200},
    {'key': 'total', 'name': 'المجموع', 'group_name': '', 'col_type': 'grand_total', 'color': '#FFFFFF', 'max_value': 500},
]

# ---------------------------------------------------------------------------
# Third term — أجهزة مكتبية
# ---------------------------------------------------------------------------
# Visual left → right from screenshot:
# المجموع 500 | العملي 200 | رسم دوائر الكترونية 100 | لغة إنجليزية 50 | ميكانيكا 50 |
# تكنولوجيا 100 | الفصل | الاسم | الرقم السري | رقم الجلوس | م
# All included: 100+50+50+100+200 = 500
THIRD_TERM_OFFICE_EQUIPMENT_COLUMNS = [
    {'key': 'serial', 'name': 'م', 'group_name': '', 'col_type': 'serial', 'color': '#6FA8DC', 'max_value': 0},
    {'key': 'seat_number', 'name': 'رقم الجلوس', 'group_name': '', 'col_type': 'seat_number', 'color': '#FFFFFF', 'max_value': 0},
    {'key': 'pin_number', 'name': 'الرقم السري', 'group_name': '', 'col_type': 'pin_number', 'color': '#FFFFFF', 'max_value': 0},
    {'key': 'name', 'name': 'الاسم', 'group_name': '', 'col_type': 'name', 'color': '#F5C080', 'max_value': 0},
    {'key': 'class', 'name': 'الفصل', 'group_name': '', 'col_type': 'class', 'color': '#F5C080', 'max_value': 0},
    {'key': 'technology', 'name': 'تكنولوجيا', 'group_name': '', 'col_type': 'score', 'color': '#B6D7A8', 'max_value': 100},
    {'key': 'mechanics', 'name': 'ميكانيكا', 'group_name': '', 'col_type': 'score', 'color': '#F9CB9C', 'max_value': 50},
    {'key': 'english', 'name': 'لغة إنجليزية', 'group_name': '', 'col_type': 'score', 'color': '#CC4125', 'max_value': 50},
    {'key': 'circuit_draw', 'name': 'رسم دوائر الكترونية', 'group_name': '', 'col_type': 'score', 'color': '#FFE599', 'max_value': 100},
    {'key': 'practical', 'name': 'العملي', 'group_name': '', 'col_type': 'score', 'color': '#B45F06', 'max_value': 200},
    {'key': 'total', 'name': 'المجموع', 'group_name': '', 'col_type': 'total', 'color': '#FFFFFF', 'max_value': 500},
]

# ---------------------------------------------------------------------------
# Health Insurance report — تقرير التأمين الصحي
# ---------------------------------------------------------------------------
# Visual left → right from screenshot (RTL):
# رقم الموبايل | الرقم القومي | الرقم التأميني | الاسم | م
# Yellow header row; logo header (Ministry / PVTD / SMART) on Excel export
HEALTH_INSURANCE_COLUMNS = [
    {'key': 'serial', 'name': 'م', 'group_name': '', 'col_type': 'serial', 'color': '#FFFFFF', 'max_value': 0},
    {'key': 'name', 'name': 'الاسم', 'group_name': '', 'col_type': 'name', 'color': '#FFFFFF', 'max_value': 0},
    {'key': 'insurance_number', 'name': 'الرقم التأميني', 'group_name': '', 'col_type': 'text', 'color': '#FFFFFF', 'max_value': 0},
    {'key': 'national_id', 'name': 'الرقم القومي', 'group_name': '', 'col_type': 'text', 'color': '#FFFFFF', 'max_value': 0},
    {'key': 'mobile', 'name': 'رقم الموبايل', 'group_name': '', 'col_type': 'text', 'color': '#FFFFFF', 'max_value': 0},
]

# ---------------------------------------------------------------------------
# Form 27 — نموذج 27 (كشف أسماء الطلاب المقيدون بالصف الأول)
# ---------------------------------------------------------------------------
# Visual left → right from screenshot (RTL):
# ملاحظات | التليفون | محافظة السكن | محل الاقامة | سنة | شهر | يوم | الديانة |
# الجنسية | النوع | الرقم القومي | رقم التسجيل | الاسم | م
FORM_27_HEADER_COLOR = '#D9D9D9'
FORM_27_COLUMNS = [
    {'key': 'serial', 'name': 'م', 'group_name': '', 'col_type': 'serial', 'color': FORM_27_HEADER_COLOR, 'max_value': 0},
    {'key': 'name', 'name': 'الاسم', 'group_name': '', 'col_type': 'name', 'color': FORM_27_HEADER_COLOR, 'max_value': 0},
    {'key': 'registration_number', 'name': 'رقم التسجيل', 'group_name': '', 'col_type': 'text', 'color': FORM_27_HEADER_COLOR, 'max_value': 0},
    {'key': 'national_id', 'name': 'الرقم القومي', 'group_name': '', 'col_type': 'text', 'color': FORM_27_HEADER_COLOR, 'max_value': 0},
    {'key': 'gender', 'name': 'النوع', 'group_name': '', 'col_type': 'text', 'color': FORM_27_HEADER_COLOR, 'max_value': 0},
    {'key': 'nationality', 'name': 'الجنسية', 'group_name': '', 'col_type': 'text', 'color': FORM_27_HEADER_COLOR, 'max_value': 0},
    {'key': 'religion', 'name': 'الديانة', 'group_name': '', 'col_type': 'text', 'color': FORM_27_HEADER_COLOR, 'max_value': 0},
    {'key': 'birth_day', 'name': 'يوم', 'group_name': 'تاريخ الميلاد', 'col_type': 'text', 'color': FORM_27_HEADER_COLOR, 'max_value': 0},
    {'key': 'birth_month', 'name': 'شهر', 'group_name': 'تاريخ الميلاد', 'col_type': 'text', 'color': FORM_27_HEADER_COLOR, 'max_value': 0},
    {'key': 'birth_year', 'name': 'سنة', 'group_name': 'تاريخ الميلاد', 'col_type': 'text', 'color': FORM_27_HEADER_COLOR, 'max_value': 0},
    {'key': 'residence', 'name': 'محل الاقامة', 'group_name': '', 'col_type': 'text', 'color': FORM_27_HEADER_COLOR, 'max_value': 0},
    {'key': 'governorate', 'name': 'محافظة السكن', 'group_name': '', 'col_type': 'text', 'color': FORM_27_HEADER_COLOR, 'max_value': 0},
    {'key': 'phone', 'name': 'التليفون', 'group_name': '', 'col_type': 'text', 'color': FORM_27_HEADER_COLOR, 'max_value': 0},
    {'key': 'notes', 'name': 'ملاحظات', 'group_name': '', 'col_type': 'text', 'color': FORM_27_HEADER_COLOR, 'max_value': 0},
]

# (term, term_types) → column layout
TEMPLATE_COLUMNS = {
    ('first', None): FIRST_TERM_COLUMNS,
    ('second', 'industrial_electronics'): SECOND_TERM_INDUSTRIAL_ELECTRONICS_COLUMNS,
    ('second', 'industrial_electricity'): SECOND_TERM_INDUSTRIAL_ELECTRICITY_COLUMNS,
    ('second', 'computer'): SECOND_TERM_COMPUTER_COLUMNS,
    ('second', 'office_equipment'): SECOND_TERM_OFFICE_EQUIPMENT_COLUMNS,
    ('third', 'computer'): THIRD_TERM_COMPUTER_COLUMNS,
    ('third', 'industrial_electronics'): THIRD_TERM_INDUSTRIAL_ELECTRONICS_COLUMNS,
    ('third', 'industrial_electricity'): THIRD_TERM_INDUSTRIAL_ELECTRICITY_COLUMNS,
    ('third', 'office_equipment'): THIRD_TERM_OFFICE_EQUIPMENT_COLUMNS,
}


def get_template_columns(term='first', term_types=None, mold_kind='grades'):
    """Return the column layout for a mold kind / term + specialization."""
    if mold_kind == 'health_insurance':
        return HEALTH_INSURANCE_COLUMNS
    if mold_kind == 'form_27':
        return FORM_27_COLUMNS
    if term == 'second' and term_types == 'industrial_electronics':
        return SECOND_TERM_INDUSTRIAL_ELECTRONICS_COLUMNS
    if term == 'second' and term_types == 'industrial_electricity':
        return SECOND_TERM_INDUSTRIAL_ELECTRICITY_COLUMNS
    if term == 'second' and term_types == 'computer':
        return SECOND_TERM_COMPUTER_COLUMNS
    if term == 'second' and term_types == 'office_equipment':
        return SECOND_TERM_OFFICE_EQUIPMENT_COLUMNS
    if term == 'third' and term_types == 'computer':
        return THIRD_TERM_COMPUTER_COLUMNS
    if term == 'third' and term_types == 'industrial_electronics':
        return THIRD_TERM_INDUSTRIAL_ELECTRONICS_COLUMNS
    if term == 'third' and term_types == 'industrial_electricity':
        return THIRD_TERM_INDUSTRIAL_ELECTRICITY_COLUMNS
    if term == 'third' and term_types == 'office_equipment':
        return THIRD_TERM_OFFICE_EQUIPMENT_COLUMNS
    if term == 'first':
        return FIRST_TERM_COLUMNS
    # Fallback: first-term layout until more second/third templates exist
    return FIRST_TERM_COLUMNS
