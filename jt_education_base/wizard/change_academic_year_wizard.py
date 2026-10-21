from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ChangeAcademicYearWizard(models.TransientModel):
    _name = "change.year.wizard"
    _description = "Change Year Wizard"

    reason_to_change = fields.Selection([
        ('wrong_selection', 'Wrong Selection'),
        ('standard_upgrade', 'Standard Upgrade'),
    ])
    current_year = fields.Many2one('year.year', string='العام الدراسي الحالي', readonly=True)
    year_to_change = fields.Many2one('year.year', string='العام الدراسي الجديد')
    current_standard = fields.Many2one('student.standard', string='الصف الحالي', readonly=True)
    standard_to_change = fields.Many2one('student.standard', string='الصف الجديد')
    current_division = fields.Many2one('standard.division', string='القسم الحالي', readonly=True)
    division_to_change = fields.Many2one(
        'standard.division',
        string='القسم الجديد',
    )
    current_class = fields.Many2one('student.class', string='الفصل الحالي', readonly=True)
    class_to_change = fields.Many2one('student.class', string='الفصل الجديد')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if active_id:
            partner = self.env['res.partner'].browse(active_id)
            res.update({
                'current_year': partner.curr_year.id,
                'year_to_change': partner.curr_year.id,
                'current_standard': partner.standard.id,
                'standard_to_change': partner.standard.id,
                'current_division': partner.div.id,
                'division_to_change': partner.div.id,
                'current_class': partner.class_id.id,
                'class_to_change': partner.class_id.id,
            })
        return res

    def _check_no_fee_remaining(self, partner):
        """Block the move while the student still owes fees."""
        if 'student.fee.plan' not in self.env:
            return
        plans = self.env['student.fee.plan'].search([
            ('student_id', '=', partner.id),
            ('remaining', '>', 0),
        ])
        if plans:
            amount = sum(plans.mapped('remaining'))
            raise UserError(_(
                'لا يمكن تغيير العام الدراسي أو الصف أو القسم أو الفصل. '
                'يوجد مبلغ متبقي %(amount).2f على خطة رسوم هذا الطالب.',
                amount=amount,
            ))

    def year_to_change_button(self):
        active_id = self.env.context.get('active_id')
        if not active_id:
            return
        partner = self.env['res.partner'].browse(active_id)
        self._check_no_fee_remaining(partner)
        unchanged = (
            partner.curr_year == self.year_to_change
            and partner.standard == self.standard_to_change
            and partner.div == self.division_to_change
            and partner.class_id == self.class_to_change
        )
        if not all([
            self.year_to_change, self.standard_to_change,
            self.division_to_change, self.class_to_change,
        ]):
            raise ValidationError(_('اختر العام الدراسي والصف والقسم والفصل الجديد.'))
        if unchanged:
            raise ValidationError(_(
                'لم يتم تغيير العام الدراسي أو الصف أو القسم أو الفصل.'
            ))
        partner.write({
            'curr_year': self.year_to_change.id,
            'standard': self.standard_to_change.id,
            'div': self.division_to_change.id,
            'class_id': self.class_to_change.id,
        })
        self.env['student.history'].create({
            'student_id': partner.id,
            'year_changed_from': self.current_year.id,
            'year_changed_to': self.year_to_change.id,
            'reason': self.reason_to_change,
        })
