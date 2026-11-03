# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


# Default companies (existing options)
VIOLATION_TYPE_DEFAULT = [
    ('fighting', 'المشاجرة أو إيذاء زميله'),
    ('bullying', 'التنمر والألفاظ غير اللائقة'),
    ('filming', 'تصوير أو نشر مقاطع من داخل المحطة'),
    ('uniform', 'عدم الالتزام بالزي المدرسي'),
    ('late_morning', 'التأخر الصباحي عن موعد المدرسة'),
    ('no_books', 'عدم إحضار الكتب والأدوات المدرسية'),
    ('mobile', 'عدم تسليم الموبايل للمشرف المختص'),
    ('disrespect_staff', 'إساءة الأدب مع هيئة التدريس'),
    ('theft', 'السرقة'),
    ('smoking', 'التدخين'),
    ('drugs_weapons', 'حيازة المخدرات والسلاح'),
    ('truancy', 'الهروب من المدرسة'),
    ('cheating', 'الغش في الاختبارات'),
    ('vandalism', 'تخريب الممتلكات'),
    ('class_permission', 'الدخول أو الخروج من الفصل بدون استئذان'),
    ('bus_misbehavior', 'السلوكيات الخاطئة داخل الباص'),
]

ACTION_TAKEN_DEFAULT = [
    ('verbal_warning', 'تنبيه شفوي'),
    ('warning', 'إنذار'),
    ('expulsion', 'فصل'),
    ('call_guardian', 'استدعاء ولي الأمر'),
    ('caution', 'تحذير'),
    ('written_pledge', 'تعهد كتابي'),
    ('lower_behavior_grades', 'خفض درجات السلوك'),
    ('deny_entry_same_day', 'عدم دخول المدرسة في نفس اليوم'),
    ('bar_activities', 'عدم الاشتراك في الأنشطة'),
    ('suspend_pending', 'إيقاف الطالب لحين اتخاذ إجراء مناسب'),
    ('suspend_15_days', 'فصل لمدة 15 يوم'),
    ('lower_teacher_grades', 'خفض درجات من جانب المعلم'),
    ('case_study', 'دراسة حالة'),
]

# بني مزار — مخالفات الدرجة الأولى (البسيطة)
VIOLATION_TYPE_BANI_MAZAR_D1 = [
    ('d1_101', 'التأخر عن الاصطفاف الصباحي وعدم المشاركة فيه بدون عذر مقبول'),
    ('d1_102', 'التأخر عن الزمن المحدد لبدء الحصة بدون عذر مقبول'),
    ('d1_103', 'عدم التقيد بالزي المدرسي أو الرياضي الخاص بالمدرسة بدون عذر مقبول'),
    ('d1_104', 'إطالة الشعر للبنين أو القصات الغريبة للبنين والبنات'),
    ('d1_105', 'عدم إحضار الكتب والأدوات المدرسية بدون عذر مقبول'),
    ('d1_106', 'عدم الالتزام بقواعد السلوك الإيجابي داخل الصف أو خارجه، مثل عدم المحافظة على الهدوء والانضباط أثناء الحصة وإصدار أصوات غير لائقة'),
    ('d1_107', 'النوم أثناء الحصص أو الأنشطة المدرسية الرسمية بدون مبرر أو عذر مرضي بعد التأكد من الحالة الصحية'),
    ('d1_108', 'تناول الطعام أثناء الحصص والاصطفاف الصباحي بدون مبرر أو إذن وبعد التأكد من الحالة الصحية للطالب'),
    ('d1_109', 'عدم تأدية الواجبات والمهام المكلفة بها في الوقت المحدد'),
    ('d1_110', 'سوء استخدام الأجهزة الإلكترونية كالأجهزة اللوحية وغيرها أثناء الحصص، ويشمل ذلك ممارسة الألعاب غير التعليمية وارتداء السماعات'),
    ('d1_111', 'كل ما يماثل هذه المخالفات مما تقرره لجنة الحماية المدرسية'),
]

# بني مزار — مخالفات الدرجة الثانية (متوسطة الخطورة)
VIOLATION_TYPE_BANI_MAZAR_D2 = [
    ('d2_201', 'التغيب عن المدرسة دون عذر مقبول في أي وقت بما فيها قبل وبعد الإجازات والعطل ونهاية الأسبوع وقبل الامتحانات'),
    ('d2_202', 'الدخول إلى الفصل والخروج منه وقت الحصة دون استئذان'),
    ('d2_203', 'عدم حضور الأنشطة والفعاليات المدرسية دون عذر مقبول'),
    ('d2_204', 'التحريض على الشجار أو تهديد أو تخويف أي من الزملاء في المدرسة'),
    ('d2_205', 'إتيان ما من شأنه مخالفة الآداب العامة أو النظام العام بالمدرسة وقيم وعادات المجتمع كالتشبه بالجنس الآخر في الملبس والمظهر كسمات الشعر ووضع مساحيق التجميل على سبيل المثال'),
    ('d2_206', 'الكتابة على الأثاث المدرسي أو مقاعد الحافلات المدرسية أو اللعب بجرس الإنذار أو المصعد'),
    ('d2_207', 'إحضار الهاتف المحمول أو إساءة استعمال أي من وسائل الاتصال'),
    ('d2_208', 'كل ما هو شبيه بهذه المخالفات وفق تقدير لجنة الحماية المدرسية'),
]

# بني مزار — مخالفات الدرجة الثالثة (شديدة الخطورة)
VIOLATION_TYPE_BANI_MAZAR_D3 = [
    ('d3_301', 'التنمر بأنواعه وأشكاله المختلفة'),
    ('d3_302', 'الغش أو الشروع فيه'),
    ('d3_303', 'نقل ونسخ الواجبات والتقارير والأبحاث أو المشاريع ونسبتها لنفسه'),
    ('d3_304', 'الإساءة اللفظية والتطاول على الطلاب أو العاملين أو ضيوف المدرسة'),
    ('d3_305', 'التدخين داخل حرم المدرسة وحيازة أدواته'),
    ('d3_306', 'رفض التجاوب مع تعليمات التفتيش أو تسليم المواد الممنوعة'),
    ('d3_307', 'الخروج من المدرسة دون إذن أو الهروب منها أثناء اليوم الدراسي'),
    ('d3_308', 'محاولة التشهير بالزملاء والعاملين بالمدرسة في وسائل التواصل الاجتماعي والإساءة لهم'),
    ('d3_309', 'انتحال صفة الغير في المعاملات المدرسية أو تزوير الوثائق الخاصة'),
    ('d3_310', 'إتلاف أو تخريب أثاث وأدوات المدرسة ومرافقها والاستيلاء عليها'),
    ('d3_311', 'العبث والتخريب وإتلاف الحافلات المدرسية وإيذاء السائق أو المشرف أو مستخدمي الطريق'),
    ('d3_312', 'الاعتداء على سلامة جسد الآخرين بالمدرسة غير المؤدي إلى حدوث أي إصابات للمعتدى عليه'),
    ('d3_313', 'عدم اتباع تعليمات الأمن والسلامة'),
    ('d3_314', 'تصوير وحيازة ونشر وتداول صور العاملين بالمدرسة والطلاب دون إذن'),
    ('d3_315', 'كل ما هو شبيه بهذه المخالفات وفق تقدير لجنة الحماية المدرسية'),
]

VIOLATION_TYPE_BANI_MAZAR = (
    VIOLATION_TYPE_BANI_MAZAR_D1
    + VIOLATION_TYPE_BANI_MAZAR_D2
    + VIOLATION_TYPE_BANI_MAZAR_D3
)

ACTION_TAKEN_BANI_MAZAR = [
    ('d1_verbal_warning', 'التنبيه الشفوي'),
    ('d1_written_warning', 'التنبيه الكتابي'),
    ('d1_extra_school_tasks', 'قيام الطالب بأداء مهام مدرسية إضافية بعد انتهاء اليوم الدراسي'),
    ('d1_extra_school_work', 'قيام الطالب بأداء مهام وأعمال أخرى مدرسية إضافية بعد انتهاء اليوم الدراسي'),
    ('d1_deduct_behavior_marks', 'خصم بعض أو كل درجات السلوك في مادة أو أكثر'),
    ('d2_refer_social_worker', 'تحويل الطالب للأخصائي الاجتماعي'),
    ('d2_call_guardian', 'استدعاء ولي الأمر'),
    ('d2_suspend_one_week', 'الفصل المؤقت من المدرسة لمدة أسبوع'),
    ('d3_suspend_two_weeks', 'الفصل المؤقت من المدرسة لمدة أسبوعين'),
    ('d3_suspend_until_semester_end', 'الفصل المؤقت من المدرسة حتى نهاية الفصل الدراسي'),
    ('d3_suspend_full_year', 'الفصل المؤقت من المدرسة لمدة عام دراسي كامل'),
    ('d3_disciplinary_transfer', 'النقل تأديباً إلى مدرسة أخرى'),
    ('d3_external_study', 'تحويل الطالب لنظام الدراسة من الخارج'),
]

# مدرسة سمارت للتمريض — مخالفات الدرجة الأولى
VIOLATION_TYPE_SMART_NURSING_D1 = [
    ('sn_late_morning', 'التأخر الصباحي'),
    ('sn_uniform', 'عدم الالتزام بالزي المدرسي'),
    ('sn_negative_outside', 'السلوكيات السلبية خارج الفصل (إلقاء القمامة - رفع الصوت - الشغب)'),
    ('sn_repeated_absence', 'الغياب المتكرر بدون عذر'),
    ('sn_appearance', 'المظهر العام غير اللائق (اكسسوارات - قصات شعر - مكياج)'),
    ('sn_no_books', 'عدم إحضار الكتب أو الأدوات'),
    ('sn_class_permission', 'الدخول والخروج من الفصل بدون استئذان'),
    ('sn_neglect_tasks', 'إهمال الواجبات'),
    ('sn_inappropriate_speech', 'التحدث بشكل غير لائق مع العاملين أو المعلمين'),
    ('sn_negative_inside', 'السلوكيات السلبية داخل الفصل (إعاقة الدرس - الكلام الجانبي)'),
    ('sn_damage_peer_tools', 'إتلاف أدوات زميل'),
    ('sn_ignore_supervision', 'عدم اتباع تعليمات الإشراف'),
    ('sn_change_seat', 'تغيير المقاعد بالفصل وأخذ مكان زميل'),
    ('sn_repeated_sleeping', 'النوم المتكرر داخل الفصل'),
    ('sn_throw_windows', 'إلقاء أشياء من النوافذ'),
    ('sn_disrupt_class', 'تعطيل الحصة والتحريض على الشغب'),
    ('sn_intentional_push', 'الدفع المتعمد وتعريض الطلاب للخطر'),
]

# مدرسة سمارت للتمريض — مخالفات الدرجة الثانية
VIOLATION_TYPE_SMART_NURSING_D2 = [
    ('sn_d2_no_phone', 'عدم تسليم الهاتف للمشرف'),
    ('sn_d2_bullying', 'التنمر'),
    ('sn_d2_cheat_monthly', 'الغش في امتحانات الشهر'),
    ('sn_d2_cheat_mid_final', 'الغش في امتحانات نصف ونهاية العام الدراسي'),
    ('sn_d2_damage_property', 'إتلاف ممتلكات المدرسة عمداً'),
    ('sn_d2_escape_school', 'الهروب من المدرسة'),
    ('sn_d2_tamper_safety', 'العبث بوسائل الأمن والسلامة'),
    ('sn_d2_forge_signature', 'تزوير توقيع ولي الأمر'),
    ('sn_d2_opposite_sex_contact', 'التواصل مع الجنس الآخر من الطلاب'),
    ('sn_d2_publish_data', 'نشر بيانات أشخاص دون تصريح'),
    ('sn_d2_foul_language', 'السب والتلفظ بألفاظ خارجة'),
    ('sn_d2_incite_fight', 'التحريض على الشجار وإثارة الفوضى والسلوك العدواني والشجار الدائم مع الطلاب'),
    ('sn_d2_hospital_disturbance', 'إحداث شغب داخل المستشفيات أثناء التدريب العملي'),
]

# مدرسة سمارت للتمريض — مخالفات الدرجة الثالثة
VIOLATION_TYPE_SMART_NURSING_D3 = [
    ('sn_d3_theft', 'السرقة'),
    ('sn_d3_aggressive_students', 'السلوك العدواني مع الطلاب'),
    ('sn_d3_smoking', 'التدخين وحيازة منتجات التدخين بكافة أنواعها'),
    ('sn_d3_verbal_abuse_staff', 'التطاول اللفظي على الإشراف أو المدرسين'),
    ('sn_d3_drugs_weapons', 'حيازة المخدرات أو السلاح'),
    ('sn_d3_physical_assault_student', 'الاعتداء البدني على طالب آخر'),
    ('sn_d3_strike_staff', 'التطاول باليد على أحد المشرفين أو المعلمين'),
    ('sn_d3_cause_injury', 'إحداث إصابة أو عاهة لطالب آخر'),
    ('sn_d3_bully_teacher', 'التنمر على المدرس'),
    ('sn_d3_politics_religion_sex', 'التحدث في السياسة أو الدين أو الجنس'),
    ('sn_d3_disclose_patient_data', 'إفشاء بيانات المرضى أو المعلومات الصحية السرية أثناء التدريب'),
    ('sn_d3_harassment', 'التحرش بكافة أنواعه وأشكاله'),
    ('sn_d3_threat_assault', 'التهديد بالاعتداء'),
    ('sn_d3_threaten_safety', 'القيام بسلوك يهدد بسلامة الآخرين'),
    ('sn_d3_self_harm', 'تعمد إيذاء النفس بكافة أشكاله'),
    ('sn_d3_film_campus_social', 'التصوير داخل حرم المدرسة ونشر المحتوى على وسائل التواصل الاجتماعي'),
    ('sn_d3_film_teacher', 'تصوير المعلم داخل الفصل'),
    ('sn_d3_defame_school_social', 'التحدث بشكل غير لائق عن المدرسة على وسائل التواصل الاجتماعي'),
]

VIOLATION_TYPE_SMART_NURSING = (
    VIOLATION_TYPE_SMART_NURSING_D1
    + VIOLATION_TYPE_SMART_NURSING_D2
    + VIOLATION_TYPE_SMART_NURSING_D3
)

ACTION_TAKEN_SMART_NURSING = [
    ('sn_verbal_warning', 'تنبيه شفوي'),
    ('sn_verbal_warn_inform_guardian', 'تنبيه شفوي + إعلام ولي الأمر'),
    ('sn_verbal_warn_record', 'تنبيه شفوي + تسجيل المخالفة'),
    ('sn_verbal_warn_keep_seat', 'تنبيه شفوي وإلزام الطالب بمكانه'),
    ('sn_guidance', 'التوجيه والإرشاد'),
    ('sn_inform_guardian', 'إعلام ولي الأمر'),
    ('sn_notify_guardian', 'إبلاغ ولي الأمر'),
    ('sn_inform_guardian_warn_sign', 'إعلام ولي الأمر + إنذار وتوقيع الطالب'),
    ('sn_notify_guardian_warn_sign', 'إبلاغ ولي الأمر + عمل إنذار وإقرار بتوقيع الطالب'),
    ('sn_warn_student_sign', 'إنذار وتوقيع الطالب'),
    ('sn_warn_pledge_signed', 'إنذار وتعهد موقع من الطالب'),
    ('sn_written_warning', 'إنذار كتابي'),
    ('sn_written_warn_sign', 'إنذار كتابي + توقيع الطالب'),
    ('sn_written_warn_acknowledgment', 'إنذار كتابي + إقرار بتوقيع الطالب'),
    ('sn_written_warn_guidance', 'إنذار كتابي + توجيه وإرشاد'),
    ('sn_guidance_no_repeat', 'التوجيه والإرشاد وإنذار بعدم التكرار'),
    ('sn_call_guardian', 'استدعاء ولي الأمر'),
    ('sn_call_guardian_pledge', 'استدعاء ولي الأمر + تعهد كتابي'),
    ('sn_call_guardian_written_ack', 'استدعاء ولي الأمر + إقرار كتابي'),
    ('sn_call_guardian_absence_reason', 'استدعاء ولي الأمر + تقديم مبرر للغياب'),
    ('sn_call_guardian_written_report', 'استدعاء ولي الأمر + تقرير كتابي'),
    ('sn_call_guardian_report_pledge', 'استدعاء ولي الأمر + محضر رسمي + تعهد كتابي'),
    ('sn_call_guardian_cover_damage', 'استدعاء ولي الأمر + تحمل التلفيات'),
    ('sn_contact_guardian_reasons', 'التواصل مع ولي الأمر لمعرفة الأسباب'),
    ('sn_deny_entry_inform_guardian', 'عدم دخول المدرسة في نفس اليوم + إعلام ولي الأمر'),
    ('sn_bar_activities', 'الحرمان من الاشتراك في الأنشطة'),
    ('sn_attach_absence_file', 'إرفاق نسبة الغياب بملف شؤون الطلبة'),
    ('sn_deduct_year_work', 'خصم درجات أعمال السنة من جانب المعلم'),
    ('sn_teacher_class_penalty', 'المعلم يوقع العقوبة المناسبة داخل الفصل'),
    ('sn_class_orientation_warn', 'إنذار توجيهي بالفصل'),
    ('sn_warn_deduct_behavior', 'إنذار مع خصم درجات السلوك'),
    ('sn_deduct_behavior', 'خصم درجات السلوك'),
    ('sn_deduct_behavior_teacher', 'خصم درجات السلوك من جانب المعلم'),
    ('sn_confiscate_phone_24h', 'حجز الهاتف ٢٤ ساعة'),
    ('sn_confiscate_phone_3d', 'حجز الهاتف لمدة ٣ أيام مع إخطار ولي الأمر'),
    ('sn_warn_expulsion', 'إنذار بالفصل'),
    ('sn_report_warn_expulsion', 'عمل محضر وإنذار بالفصل'),
    ('sn_cover_damage_report_warn', 'تحمل الطالب تكلفة التلفيات + عمل محضر رسمي وإنذار بالفصل'),
    ('sn_cover_damage_suspend_3d', 'تحمل الطالب تكلفة التلفيات + فصل ٣ أيام'),
    ('sn_cover_damage_suspend_board', 'تحمل الطالب تكلفة التلفيات + عمل محضر فصل بعد موافقة رئيس مجلس الإدارة'),
    ('sn_refer_committee_call_guardian', 'تحويل الطالب إلى لجنة خاصة + استدعاء ولي الأمر'),
    ('sn_ministry_regulation_decision', 'اتخاذ قرار طبقاً للائحة الوزارة'),
    ('sn_case_study_guidance', 'دراسة الحالة والتوجيه والإرشاد'),
    ('sn_guidance_written_warn', 'التوجيه والإرشاد + إنذار كتابي'),
    ('sn_written_warn_ack_apology', 'إنذار كتابي وإقرار بتوقيع الطالب + تقديم الاعتذار'),
    ('sn_call_guardian_official_report', 'استدعاء ولي الأمر + محضر رسمي'),
    ('sn_call_guardian_report_and_pledge', 'استدعاء ولي الأمر + محضر رسمي وتعهد كتابي'),
    ('sn_call_guardian_report_suspend_1d', 'استدعاء ولي الأمر + محضر رسمي + فصل يوم'),
    ('sn_call_guardian_pledge_suspend_1d', 'استدعاء ولي الأمر + تعهد كتابي + فصل يوم'),
    ('sn_call_guardian_suspend_3d', 'استدعاء ولي الأمر + فصل لمدة ٣ أيام'),
    ('sn_notify_and_call_guardian', 'إخطار ولي الأمر واستدعائه'),
    ('sn_psychological_case_study', 'دراسة الحالة من الناحية النفسية'),
    ('sn_confiscate_phone_24h_notify_report', 'حجز الهاتف لمدة ٢٤ ساعة + إبلاغ ولي الأمر + محضر رسمي'),
    ('sn_confiscate_phone_3d_warn_pledge', 'حجز الهاتف لمدة ٣ أيام + إنذار بالفصل + تعهد كتابي'),
    ('sn_suspend_one_day', 'فصل يوم واحد'),
    ('sn_suspend_two_days', 'فصل يومين'),
    ('sn_suspend_two_days_deduct', 'فصل يومين + خصم من درجات السلوك'),
    ('sn_suspend_three_days', 'فصل ٣ أيام'),
    ('sn_suspend_one_week', 'فصل لمدة أسبوع'),
    ('sn_report_suspend_one_day', 'محضر رسمي + فصل يوم'),
    ('sn_suspend_pending_board', 'إيقاف الطالب لحين اتخاذ إجراء من رئيس مجلس الإدارة'),
    ('sn_suspend_full_year_board', 'فصل عام دراسي كامل بعد اعتماد رئيس مجلس الإدارة'),
]

BANI_MAZAR_COMPANY_NAME = 'بني مزار'
SMART_NURSING_COMPANY_NAME = 'سمارت للتمريض'


class StudentViolation(models.Model):
    _name = 'student.violation'
    _description = 'مخالفة الطالب'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        required=True,
        index=True,
        default=lambda self: self.env.company,
        tracking=True,
    )
    student_id = fields.Many2one(
        'res.partner',
        string='الطالب',
        required=True,
        domain="[('is_student', '=', True), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        tracking=True,
        ondelete='cascade',
    )
    stud_id = fields.Char(related='student_id.stud_id', string='رقم الطالب', store=True, readonly=True)
    father_name = fields.Char(related='student_id.father_name', string='اسم الأب', readonly=True)
    surname = fields.Char(related='student_id.surname', string='اللقب', readonly=True)
    standard_id = fields.Many2one(
        related='student_id.standard',
        string='الصف',
        store=True,
        readonly=True,
    )
    class_id = fields.Many2one(
        'student.class',
        string='الفصل',
        tracking=True,
    )
    div_id = fields.Many2one(
        'standard.division',
        string='الشعبة',
        tracking=True,
    )
    date = fields.Date(
        string='التاريخ',
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    violation_type = fields.Selection(
        selection='_selection_violation_type',
        string='المخالفات',
        required=True,
        tracking=True,
    )
    action_taken = fields.Selection(
        selection='_selection_action_taken',
        string='الإجراء المتخذ مع الطالب',
        tracking=True,
    )
    notes = fields.Text(string='الملاحظات')
    description = fields.Text(string='وصف المشكلة')

    @api.model
    def _selection_violation_type(self):
        # Store all keys so existing records remain valid across companies.
        return (
            VIOLATION_TYPE_DEFAULT
            + VIOLATION_TYPE_BANI_MAZAR
            + VIOLATION_TYPE_SMART_NURSING
        )

    @api.model
    def _selection_action_taken(self):
        return (
            ACTION_TAKEN_DEFAULT
            + ACTION_TAKEN_BANI_MAZAR
            + ACTION_TAKEN_SMART_NURSING
        )

    @api.model
    def _company_name(self, company=None):
        company = company or self.env.company
        return (company.name or '').strip()

    @api.model
    def _is_bani_mazar_company(self, company=None):
        return BANI_MAZAR_COMPANY_NAME in self._company_name(company)

    @api.model
    def _is_smart_nursing_company(self, company=None):
        return SMART_NURSING_COMPANY_NAME in self._company_name(company)

    @api.model
    def _get_violation_type_selection_for_company(self, company=None):
        if self._is_bani_mazar_company(company):
            return list(VIOLATION_TYPE_BANI_MAZAR)
        if self._is_smart_nursing_company(company):
            return list(VIOLATION_TYPE_SMART_NURSING)
        return list(VIOLATION_TYPE_DEFAULT)

    @api.model
    def _get_action_taken_selection_for_company(self, company=None):
        if self._is_bani_mazar_company(company):
            return list(ACTION_TAKEN_BANI_MAZAR)
        if self._is_smart_nursing_company(company):
            return list(ACTION_TAKEN_SMART_NURSING)
        return list(ACTION_TAKEN_DEFAULT)

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields=allfields, attributes=attributes)
        company = self.env.company
        if 'violation_type' in res:
            res['violation_type']['selection'] = self._get_violation_type_selection_for_company(company)
        if 'action_taken' in res:
            res['action_taken']['selection'] = self._get_action_taken_selection_for_company(company)
        return res

    @api.depends('student_id', 'violation_type', 'date')
    def _compute_display_name(self):
        violation_labels = dict(self._selection_violation_type())
        for rec in self:
            parts = []
            if rec.student_id:
                parts.append(rec.student_id.name)
            if rec.violation_type:
                parts.append(violation_labels.get(rec.violation_type, rec.violation_type))
            if rec.date:
                parts.append(str(rec.date))
            rec.display_name = ' - '.join(parts) if parts else _('مخالفة الطالب')

    @api.onchange('company_id')
    def _onchange_company_id(self):
        allowed_violations = {
            key for key, _label in self._get_violation_type_selection_for_company(self.company_id)
        }
        allowed_actions = {
            key for key, _label in self._get_action_taken_selection_for_company(self.company_id)
        }
        if self.violation_type and self.violation_type not in allowed_violations:
            self.violation_type = False
        if self.action_taken and self.action_taken not in allowed_actions:
            self.action_taken = False

    @api.onchange('student_id')
    def _onchange_student_id(self):
        if self.student_id:
            self.class_id = self.student_id.class_id
            self.div_id = self.student_id.div
            if self.student_id.company_id:
                self.company_id = self.student_id.company_id
                self._onchange_company_id()
        else:
            self.class_id = False
            self.div_id = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('company_id'):
                vals['company_id'] = self.env.company.id
        return super().create(vals_list)
