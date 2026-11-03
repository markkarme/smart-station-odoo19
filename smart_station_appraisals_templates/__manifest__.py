# -*- coding: utf-8 -*-
{
    "name": "Smart Station Appraisals Templates",
    "version": "19.0.1.0.0",
    "category": "Human Resources/Appraisals",
    "summary": "Custom performance appraisal templates for Smart Station",
    "description": """
Smart Station Appraisals Templates
==================================

Provides ready-to-use HR appraisal templates, including:

* تقييم أداء - مدير المدرسة (School Principal / Branch Manager)
    """,
    "author": "Appivio",
    "license": "LGPL-3",
    "depends": ["hr_appraisal"],
    "data": [
        "data/hr_appraisal_notes.xml",
        "data/hr_appraisal_template_school_principal.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
