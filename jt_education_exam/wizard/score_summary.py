# -*- coding: utf-8 -*-
##############################################################################
#
#    Jupical Technologies Pvt. Ltd.
#    Copyright (C) 2018-TODAY Jupical Technologies Pvt. Ltd.(<https://www.jupical.io>).
#    Author: Jupical Technologies Pvt. Ltd.(<https://www.jupical.io>)
#    you can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    It is forbidden to publish, distribute, sublicense, or sell copies
#    of the Software or modified copies of the Software.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    GENERAL PUBLIC LICENSE (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import io
import xlsxwriter
import base64


class ScoreSummary(models.Model):
    _name = 'score.summary'
    _description = 'Score Summary Report'

    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    exam_ids = fields.Many2many('student.exam','student_exam_rel','score_id','exam_id',string="Exams")
    exam_id = fields.Many2one('student.exam', string='Select Exam')
    excel_file = fields.Binary(string='File')
    filename = fields.Char(string='File name')

    @api.onchange('start_date','end_date')
    def change_exams(self):
        if self.start_date and self.end_date:
            exams = self.env['student.exam'].search([('start_date','>=',self.start_date),('start_date','<=',self.end_date)]).ids
            if exams:
                self.exam_ids = [(6, 0, exams)]

    def get_score_summary_data(self):
        
        exam_id = self.exam_id
        results = self.env['student.result'].search([('exam_id', '=', exam_id.id)], order="total_mark_scored desc")
        result_list = []
        rank = 1
        for result in results:
            subject_line = []
            for sub_line in result.subject_line:
                subject_dict = {
                    'subject_nm': sub_line.subject_id.name,
                    'mark_scored': sub_line.mark_scored,
                }
                subject_line.append(subject_dict)

            result_dict = {
                'student': result.student_id.name,
                'pecentage': result.percentage,
                'total': result.total_mark_scored,
                'grade': result.grade_id.name,
                'paas_fail': result.pass_fail_full,
                'subject_line': subject_line,
                'rank': rank,
                'exam_id': result.exam_id.display_name
            }
            rank += 1
            result_list.append(result_dict)
        return result_list

    def generate_score_summary_report(self):
        
        self.ensure_one()
        return self.env.ref('jt_education_exam.action_score_summary_report').report_action(self.id)

    def generate_score_summary_report_xls(self):
        
        # result_list = self.get_score_summary_data()
        if self.exam_ids:
            results = self.env['student.result'].search([('exam_id', 'in', self.exam_ids.ids)])
            grade_ids = self.env['result.grade'].search([])

            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            worksheet = workbook.add_worksheet('Score Summary Report')

            headers_format = workbook.add_format({'bold': True, 'align': 'center'})
            data_format = workbook.add_format({'align': 'center', 'text_wrap': True})
            center_align_format = workbook.add_format({'align': 'center','text_wrap': True})
           
            worksheet.merge_range(0, 0, 4, 8, f'{self.env.company.name} \n\n Student Score Summary Report\n', center_align_format)
            
            headers = ['Student Name']
            col = 0  
            for exam in self.exam_ids:
                col += 1
                worksheet.merge_range(5, col, 5, col+1, exam.name, headers_format)
                for subject in exam.subject_line:
                    if subject.subject_id.name not in headers:
                        headers.append(subject.subject_id.name)
                col += 1

            headers += ['Total', 'Average', 'Grade', 'Pass/Fail', 'Rank']

            for col, header in enumerate(headers):
                worksheet.write(6, col, header, headers_format)  

            if results:
                student = [result.student_id for result in results if result and result.student_id]
                rslt_student = list(set(student))

                max_ttl = []
                for std in rslt_student:
                    results_val = self.env['student.result'].search([('student_id','=',std.id),('exam_id', 'in', self.exam_ids.ids)])
                    result_sum  = sum(results_val.mapped('total_mark_scored'))/len(self.exam_ids)
                    if result_sum not in max_ttl: 
                        max_ttl.append(result_sum)
                if max_ttl:
                    # max_index = max_ttl.index(max(max_ttl))
                    # max_ttl = [max_ttl[max_index]] + max_ttl[:max_index] + max_ttl[max_index+1:]
                    max_ttl = sorted(max_ttl,reverse=True)

                wrt_rstl_lst = []

                for w, rslt_std in enumerate(rslt_student, start=7):
                    std_rstl_val = []
                    # worksheet.write(row, 0, rslt_std.name, data_format)
                    std_rstl_val.append(rslt_std.name)
                    # col = 1
                    total_mark = 0
                    reslut_sub_count = 0
                    avrg = 0.0
                    unk_subjct = []
                    if results:
                        std_result = results.filtered(lambda x:x.student_id == rslt_std)
                        for std_rst in std_result:
                            for sbjt in std_rst.subject_line:
                                if sbjt.subject_id.id not in unk_subjct:
                                    unk_subjct.append(sbjt.subject_id.id)
                        total_mark_scored = 0
                        for sbjct_ln in unk_subjct:
                            std_result = results.filtered(lambda x:x.student_id == rslt_std)
                            for std_rst in std_result:
                                subject_line = std_rst.subject_line.search_read([('student_id','=',rslt_std.id),('exam_id','in',self.exam_ids.ids),('subject_id','=',sbjct_ln)],['id','subject_id','mark_scored'])
                                total_mark_scored = sum(item['mark_scored'] for item in subject_line)
                                subject_avg_scor = total_mark_scored / len(self.exam_ids)
                            total_mark += subject_avg_scor
                            # worksheet.write(row, col, subject_avg_scor, data_format)
                            std_rstl_val.append(subject_avg_scor)
                            # col += 1
                            reslut_sub_count += 1
                            total_mark_scored = 0

                    # worksheet.write(row, col, total_mark, data_format)
                    std_rstl_val.append(total_mark)
                    if total_mark and reslut_sub_count:
                        avrg = total_mark / reslut_sub_count
                    # worksheet.write(row, col + 1, avrg, data_format)
                    std_rstl_val.append(avrg)
                    grade = ''
                    for grade in grade_ids:
                        grade_data = grade.mark_range.split('-')
                        if int(avrg) in range(int(grade_data[0]),int(grade_data[1])):
                            grade = grade.name
                            break;
                        else:
                            grade = ''
                    # worksheet.write(row, col + 2, grade, data_format)
                    std_rstl_val.append(grade)

                    exm_results = self.env['student.result'].search([('student_id','=',rslt_std.id),('exam_id', 'in', self.exam_ids.ids)])

                    if any(not ex.pass_fail_full for ex in exm_results):
                        # worksheet.write(row, col + 3, 'Fail', data_format)
                        std_rstl_val.append('Fail')
                    else:
                        # worksheet.write(row, col + 3, 'Pass', data_format)
                        std_rstl_val.append('Pass')

                    # if any(not ex.pass_fail_full for ex in exm_results):
                    #     worksheet.write(row, col + 4, '', data_format)
                    # else:
                    if max_ttl:
                        rnk = 0
                        for clm,val in enumerate(max_ttl):
                            if val == total_mark:
                                rnk = clm + 1
                        # worksheet.write(row, col + 4, rnk, data_format)
                        std_rstl_val.append(rnk)
                    if std_rstl_val:
                        wrt_rstl_lst.append(std_rstl_val)

                reslut_sub_count = 0

            row = 7
            if wrt_rstl_lst:
                wrt_rstl_lst = sorted(wrt_rstl_lst, key=lambda x: x[-5],reverse=True)
                for rst_vals in wrt_rstl_lst:
                    col = 0
                    for rst_data in rst_vals:
                        worksheet.write(row, col, rst_data, data_format)
                        col += 1
                    row += 1

            workbook.close()

           
            xls_data = base64.encodebytes(output.getvalue())
            filename = 'Score_Summary_Report.xls'
            self.filename = filename
            self.excel_file = xls_data

            return {
                'name': 'Score Summary Report',
                'view_mode': 'form',
                'res_model': 'score.summary',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'res_id': self.id,
            }
