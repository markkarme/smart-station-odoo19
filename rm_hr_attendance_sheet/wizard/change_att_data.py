from odoo import models, fields, api, _
class attendance_sheet_line_change(models.TransientModel):
    _name = "attendance.sheet.line.change"
    _description = "Attendance Sheet Line Change"
    overtime = fields.Float("Overtime")
    late_in = fields.Float("Late In")
    diff_time = fields.Float("Diff Time")
    note = fields.Text("Note",required=True)
    att_line_id=fields.Many2one(comodel_name="attendance.sheet.line")

    @api.model
    def default_get(self, fields_list):
        res = super(attendance_sheet_line_change, self).default_get(fields_list)
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')
        if not active_model or not active_id:
            return res
        atts_line_id = self.env[active_model].browse(active_id)
        if 'overtime' in fields_list and 'overtime' not in res:
            res['overtime'] = atts_line_id.overtime
            res['late_in'] = atts_line_id.late_in
            res['diff_time'] = atts_line_id.diff_time
            res['att_line_id'] = atts_line_id.id
        return res


    def change_att_data(self):
        self.ensure_one()
        atts_line_id = self.env['attendance.sheet.line'].browse(self.env.context.get('active_id'))
        res = {
            'overtime': self.overtime,
            'late_in': self.late_in,
            'diff_time': self.diff_time,
            'note': self.note,
        }
        atts_line_id.write(res)
        # atts_line_id.att_sheet_id.calculate_att_data()
        return {'type': 'ir.actions.act_window_close'}
