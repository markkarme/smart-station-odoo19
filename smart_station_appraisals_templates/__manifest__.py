# -*- coding: utf-8 -*-
{
    "name": "Smart Station Appraisals Templates",
    "version": "19.0.1.2.6",
    "category": "Human Resources/Appraisals",
    "summary": "Custom performance appraisal templates for Smart Station",
    "description": """
Smart Station Appraisals Templates
==================================

Provides ready-to-use HR appraisal templates, including:

* تقييم أداء - مدير المدرسة (School Principal / Branch Manager)
* تقييم أداء - المدير الإداري (Administrative Manager)
* تقييم أداء - المدير الإداري (مفصل) (Administrative Manager Detailed)
* تقييم أداء - المدير الأكاديمي (Academic Director)
* تقييم أداء - مشرف الدور (Floor Supervisor)
* تقييم أداء - مشرف الدور مفصل (Floor Supervisor Detailed)
* تقييم أداء - الأخصائي النفسي (Psychologist)
* تقييم أداء - الأخصائي الاجتماعي (Social Worker)
* تقييم أداء - مدير الحسابات (Accounting Manager)
* التقييم النصف سنوي (Semi-Annual Teacher Appraisal)
* نموذج تقييم الأداء (Head of Department Appraisal)
* نموذج ملاحظة أداء رئيس القسم (Head of Department Observation)
* نموذج الملاحظة الصفية وتقييم أداء المعلم (Classroom Observation)

Also provides Job Description & KPIs document uploads under Appraisals.
    """,
    "author": "Appivio",
    "license": "LGPL-3",
    "depends": ["hr_appraisal", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "data/hr_appraisal_notes.xml",
        "data/hr_appraisal_template_school_principal.xml",
        "data/hr_appraisal_template_admin_manager_general.xml",
        "data/hr_appraisal_template_admin_manager.xml",
        "data/hr_appraisal_template_academic_director.xml",
        "data/hr_appraisal_template_floor_supervisor.xml",
        "data/hr_appraisal_template_floor_supervisor_detailed.xml",
        "data/hr_appraisal_template_psychologist.xml",
        "data/hr_appraisal_template_social_worker.xml",
        "data/hr_appraisal_template_accounting_manager.xml",
        "data/hr_appraisal_template_semi_annual.xml",
        "data/hr_appraisal_template_hod_performance.xml",
        "data/hr_appraisal_template_hod_observation.xml",
        "data/hr_appraisal_template_classroom_observation.xml",
        "views/hr_appraisal_job_description_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "smart_station_appraisals_templates/static/src/scss/appraisal_templates.scss",
            "smart_station_appraisals_templates/static/src/js/appraisal_rating_checks.js",
            "smart_station_appraisals_templates/static/src/js/job_description_file_viewer.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
