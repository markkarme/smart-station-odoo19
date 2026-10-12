# -*- coding: utf-8 -*-
import base64
import os

from markupsafe import Markup
from odoo import api, fields, models, _
from odoo.modules.module import get_module_path


class StudentCaseStudy(models.Model):
    _name = 'student.case.study'
    _description = 'دراسة حالة'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='الاسم', tracking=True)
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
        index=True,
    )
    stud_id = fields.Char(related='student_id.stud_id', string='رقم الطالب', store=True, readonly=True)
    class_id = fields.Many2one('student.class', string='الفصل', tracking=True)
    div_id = fields.Many2one('standard.division', string='الشعبة', tracking=True)
    standard_id = fields.Many2one(
        related='student_id.standard',
        string='الصف',
        store=True,
        readonly=True,
    )
    date = fields.Date(
        string='التاريخ',
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    psychologist_id = fields.Many2one(
        'res.users',
        string='الأخصائي النفسي',
        default=lambda self: self.env.user,
        tracking=True,
    )

    # ----- Page 1: Demographic -----
    gender = fields.Selection(
        selection=[('male', 'ذكر'), ('female', 'أنثى')],
        string='الجنس',
    )
    birthdate = fields.Date(string='تاريخ الميلاد')
    nationality = fields.Char(string='الجنسية')
    marital_status = fields.Selection(
        selection=[
            ('single', 'عزباء'),
            ('engaged', 'مخطوبة'),
            ('married', 'متزوجة'),
        ],
        string='الحالة الاجتماعية',
    )
    residence = fields.Char(string='أين تعيش؟')
    live_with = fields.Char(string='مع من تعيش؟')
    referral_reason = fields.Text(string='سبب الإحالة')
    family_member_ids = fields.One2many(
        'student.case.study.family',
        'case_study_id',
        string='التكوين الأسري',
    )
    has_siblings = fields.Selection(
        selection=[('yes', 'نعم'), ('no', 'لا')],
        string='هل لديك أخوات؟',
    )
    siblings_count = fields.Integer(string='كم عددهم؟')
    sibling_order = fields.Char(string='ما ترتيبك بينهم؟')

    # ----- Page 2: Childhood & Adolescence -----
    grew_up_with = fields.Selection(
        selection=[
            ('father', 'الأب'),
            ('mother', 'الأم'),
            ('both', 'كلاهما'),
            ('others', 'آخرون'),
        ],
        string='مع من نشأت؟',
    )
    birth_health_problems = fields.Text(string='هل كانت هناك مشاكل صحية أثناء ولادتك؟')
    childhood_illnesses = fields.Text(string='هل أصبت بأي أمراض أو إصابات أو حوادث أثناء طفولتك؟')
    family_economic_at_birth = fields.Text(string='ما المستوى الاقتصادي للأسرة أثناء ولادتك؟')
    family_relationships_general = fields.Text(string='صف كيف كانت العلاقات داخل الأسرة بشكل عام؟')
    relation_mother = fields.Text(string='علاقتك بوالدتك')
    relation_father = fields.Text(string='علاقتك بوالدك')
    relation_siblings = fields.Text(string='علاقتك بأخوتك')
    violence_emotional = fields.Boolean(string='عنف إنفعالي')
    violence_physical = fields.Boolean(string='عنف جسدي')
    violence_sexual = fields.Boolean(string='عنف جنسي')
    violence_neglect = fields.Boolean(string='إهمال')
    violence_description = fields.Text(string='صف ذلك')
    current_health_disease = fields.Text(string='هل تعاني من أي مرض صحي؟')
    visited_psychiatrist = fields.Selection(
        selection=[('yes', 'نعم'), ('no', 'لا')],
        string='هل سبق وزرت طبيب أو معالج نفسي من قبل؟',
    )
    psychological_complaint = fields.Text(string='ما هي الشكوى النفسية التي تعاني منها؟')

    # ----- Page 3: Interests & Symptoms -----
    receiving_treatment = fields.Text(string='هل تتلقى علاج لهذه الشكوى؟')
    hereditary_diseases = fields.Text(string='هل توجد أمراض وراثية في العائلة؟')
    do_you_work = fields.Text(string='هل تعمل؟')
    practice_sport = fields.Text(string='هل تمارس لعبة رياضية محددة؟')
    artistic_activities = fields.Text(string='هل تمارس أي من الأنشطة الفنية؟')
    any_skill = fields.Text(string='هل لديك أي مهارة؟')
    routine_habit = fields.Text(string='هل لديك عادة روتينية محددة؟')
    school_absence_period = fields.Text(
        string='حدث في فترة زمنية من عمرك لم تكن قادر على الذهاب إلى المدرسة؟ لماذا؟'
    )

    symptom_nervousness = fields.Boolean(string='عصبية')
    symptom_anxiety = fields.Boolean(string='قلق')
    symptom_decreased_interest = fields.Boolean(string='انخفاض بالاهتمام بمعظم الأنشطة')
    symptom_lack_energy = fields.Boolean(string='نقص في الطاقة')
    symptom_appetite = fields.Boolean(string='مشاكل في الشهية (عدم الشهية / شهية مفرطة)')
    symptom_weight = fields.Boolean(string='(انخفاض / زيادة) في الوزن')
    symptom_sleep = fields.Boolean(string='(أرق / نوم زائد)')
    symptom_thoughts = fields.Boolean(string='أفكار (غير عادية / غير عقلانية)')
    symptom_concentration = fields.Boolean(string='مشاكل في التركيز وانشغال ذهني بأمور كثيرة')
    symptom_memory = fields.Boolean(string='نسيان ومشاكل في الذاكرة')
    symptom_motor = fields.Boolean(string='نشاط حركي (زائد / كسل)')
    symptom_depressive = fields.Boolean(string='مزاج إكتئابي')
    symptom_isolation = fields.Boolean(string='انعزال من الأصدقاء والعائلة')
    symptom_worthlessness = fields.Boolean(string='الشعور بعدم الأهمية وفقدان الأمل')

    # ----- Page 4: Additional questions -----
    life_changes_symptoms = fields.Text(
        string='هل هناك شيء حدث أو تغير في حياتك أدى إلى ظهور أي من هذه الأعراض؟'
    )
    worst_period = fields.Text(string='ما الفترة التي شعرت أنها أسوأ وقت مررت به؟')
    self_harm_history = fields.Text(
        string='هل سبق وأن فكرت أو حاولت الانتحار أو إيذاء نفسك؟ ماذا حدث؟'
    )
    harm_others_history = fields.Text(string='هل حاولت إيذاء أحد من قبل؟ من؟ لماذا؟')
    substance_medication_history = fields.Text(
        string='هل تناولت أي عقاقير مخدرة أو حبوب أو كحوليات أو أدوية للاكتئاب أو لأي مرض نفسي آخر؟'
    )
    future_plans = fields.Text(string='هل لديك أي خطط مستقبلية؟')

    # ----- Page 5: Psychologist only -----
    general_appearance = fields.Text(string='المظهر العام')
    smile_type = fields.Selection(
        selection=[
            ('spontaneous', 'تلقائية'),
            ('artificial', 'مصطنعة'),
            ('rigid', 'جامدة'),
        ],
        string='الابتسامة',
    )
    sitting_posture = fields.Selection(
        selection=[
            ('relaxed', 'مسترخي'),
            ('alert', 'متحفز'),
            ('withdrawn', 'متقوقع'),
        ],
        string='وضعية الجلوس',
    )
    eye_contact = fields.Selection(
        selection=[('good', 'جيد'), ('not_good', 'غير جيد')],
        string='التواصل البصري ومستوى الانتباه',
    )
    movement_activity_level = fields.Text(string='مستوى الحركة والنشاط')
    thought_coherence = fields.Text(string='ترابط الأفكار والكلمات')
    voice_tone = fields.Selection(
        selection=[
            ('high', 'مرتفع'),
            ('medium', 'متوسط'),
            ('quiet', 'هادئ'),
        ],
        string='نبرة الصوت',
    )
    mood_emotional_state = fields.Text(string='الحالة المزاجية والانفعالية')
    involuntary_movements = fields.Text(string='الحركات اللاإرادية')
    physical_injuries = fields.Text(string='الإصابات والعاهات الجسدية')
    behavioral_notes = fields.Text(string='ملاحظات سلوكية')
    depression_anxiety_indicators = fields.Text(string='مؤشرات الاكتئاب أو القلق')
    initial_diagnosis = fields.Text(string='التشخيص المبدئي')
    therapeutic_goals = fields.Text(string='الأهداف العلاجية')
    treatment_plan = fields.Text(string='الخطة العلاجية')
    recommendations = fields.Text(string='التوصيات')

    @api.depends('student_id', 'name', 'date')
    def _compute_display_name(self):
        for rec in self:
            parts = [rec.name or (rec.student_id.name if rec.student_id else '')]
            if rec.date:
                parts.append(str(rec.date))
            rec.display_name = ' - '.join(p for p in parts if p) or _('دراسة حالة')

    @api.onchange('student_id')
    def _onchange_student_id(self):
        if self.student_id:
            self.name = self.student_id.name
            self.class_id = self.student_id.class_id
            self.div_id = self.student_id.div
            self.gender = self.student_id.gender
            self.birthdate = self.student_id.birthdate
            self.nationality = self.student_id.nationality
            if self.student_id.company_id:
                self.company_id = self.student_id.company_id
        else:
            self.class_id = False
            self.div_id = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('company_id'):
                vals['company_id'] = self.env.company.id
        records = super().create(vals_list)
        for rec in records:
            if not rec.family_member_ids:
                rec._create_default_family_lines()
        return records

    def _create_default_family_lines(self):
        Family = self.env['student.case.study.family']
        for rec in self:
            Family.create([
                {'case_study_id': rec.id, 'relation_type': 'father', 'sequence': 10},
                {'case_study_id': rec.id, 'relation_type': 'mother', 'sequence': 20},
                {'case_study_id': rec.id, 'relation_type': 'other', 'sequence': 30},
            ])

    def action_print_case_study(self):
        self.ensure_one()
        lang = self.env.lang if (self.env.lang or '').startswith('ar') else 'ar_001'
        return self.env.ref(
            'jt_student_violations.action_report_student_case_study'
        ).with_context(lang=lang).report_action(self)

    def get_asset_data_uri(self, filename):
        """Return a data URI for a logo so wkhtmltopdf does not need HTTP."""
        module_path = get_module_path('jt_student_violations')
        path = os.path.join(module_path, 'static', 'assets', filename)
        if not os.path.isfile(path):
            return ''
        with open(path, 'rb') as handle:
            encoded = base64.b64encode(handle.read()).decode('ascii')
        ext = os.path.splitext(filename)[1].lower().lstrip('.') or 'png'
        mime = 'jpeg' if ext in ('jpg', 'jpeg') else ext
        return 'data:image/%s;base64,%s' % (mime, encoded)

    def get_arabic_font_face_css(self):
        fonts = (
            ('normal', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
            ('bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
        )
        rules = []
        for weight, path in fonts:
            if not os.path.isfile(path):
                continue
            with open(path, 'rb') as handle:
                encoded = base64.b64encode(handle.read()).decode('ascii')
            rules.append(
                "@font-face{"
                "font-family:'ReportArabic';"
                "src:url(data:font/truetype;charset=utf-8;base64,%s) format('truetype');"
                "font-weight:%s;font-style:normal;}"
                % (encoded, weight)
            )
        return Markup(''.join(rules))

    def get_selection_label(self, field_name):
        self.ensure_one()
        value = self[field_name]
        if not value:
            return ''
        selection = dict(self._fields[field_name]._description_selection(self.env))
        return selection.get(value, value)

    def get_symptom_labels(self):
        self.ensure_one()
        mapping = [
            ('symptom_nervousness', 'عصبية'),
            ('symptom_anxiety', 'قلق'),
            ('symptom_decreased_interest', 'انخفاض بالاهتمام بمعظم الأنشطة'),
            ('symptom_lack_energy', 'نقص في الطاقة'),
            ('symptom_appetite', 'مشاكل في الشهية (عدم الشهية / شهية مفرطة)'),
            ('symptom_weight', '(انخفاض / زيادة) في الوزن'),
            ('symptom_sleep', '(أرق / نوم زائد)'),
            ('symptom_thoughts', 'أفكار (غير عادية / غير عقلانية)'),
            ('symptom_concentration', 'مشاكل في التركيز وانشغال ذهني بأمور كثيرة'),
            ('symptom_memory', 'نسيان ومشاكل في الذاكرة'),
            ('symptom_motor', 'نشاط حركي (زائد / كسل)'),
            ('symptom_depressive', 'مزاج إكتئابي'),
            ('symptom_isolation', 'انعزال من الأصدقاء والعائلة'),
            ('symptom_worthlessness', 'الشعور بعدم الأهمية وفقدان الأمل'),
        ]
        return [label for field, label in mapping if self[field]]

    def get_violence_labels(self):
        self.ensure_one()
        mapping = [
            ('violence_emotional', 'إنفعالي'),
            ('violence_physical', 'جسدي'),
            ('violence_sexual', 'جنسي'),
            ('violence_neglect', 'إهمال'),
        ]
        return [label for field, label in mapping if self[field]]
