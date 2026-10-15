# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ReportAttendanceAttendance(models.AbstractModel):
    _name = 'report.jt_education_attendance.attendance_report_template'
    _description = 'Student Attendance Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        # Web client wraps filters inside options JSON and may add these keys.
        for key in ('context', 'ids', 'model', 'options', 'report_type'):
            data.pop(key, None)

        PrintAttendance = self.env['print.attendance']
        docs = PrintAttendance.browse(docids).exists()

        # HTML report can open without a live transient record; rebuild from data.
        if not docs:
            vals = {
                'start_date': fields.Date.to_date(data['start_date']) if data.get('start_date') else False,
                'end_date': fields.Date.to_date(data['end_date']) if data.get('end_date') else False,
                'company_id': data.get('company_id') or False,
                'standard_id': data.get('standard_id') or False,
                'division_id': data.get('division_id') or False,
                'class_id': data.get('class_id') or False,
                'student_id': data.get('student_id') or False,
                'summary_report': bool(data.get('summary_report')),
            }
            docs = PrintAttendance.new(vals)

        return {
            'doc_ids': docids,
            'doc_model': 'print.attendance',
            'docs': docs,
            'data': data,
        }
