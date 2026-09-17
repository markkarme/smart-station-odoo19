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
from odoo.exceptions import ValidationError, UserError


class Memberships(models.Model):

    _name = "library.memberships"
    _description = "Library Membership details."
    _rec_name = "student_id"
    _inherit = [
                'mail.thread',
                'mail.activity.mixin',
            
               ]


    @api.model
    def expire_memberships(self):
        curr_dt = fields.Date.today()
        records = self.search([])
        for record in records:
            if (record.end_date < curr_dt):
                raise ValidationError('Membership of %s is over.' %
                                      record.student_id.name)
        #print("cron of expire memberships.....")

    @api.constrains('end_date')
    def date_constrains(self):
        delta = (self.end_date - self.start_date).days
        if delta < 30:
            raise ValidationError('User Error, Maximum allowed days for Membership is 30 days!')

    # @api.constrains('student_id')
    # def check_membership_card(self):
    #     if self.user == 'student':
    #         student_membership = self.search([('student_id', '=',
    #                                            self.student_id.id),
    #                                           ('id', 'not in', self.ids),
    #                                           ('state', '!=', 'expire')])
    #         if student_membership:
    #             raise ValidationError(
    #                 'You cannot assign Membership to same student more than once.')

    def _get_default_user(self):
        return "student"

    memberships_image = fields.Image(
        related='student_id.image_1920', store=True, attachment=True)
    memberships_code = fields.Char("Membership ID" ,copy=False)
    student_id = fields.Many2one(
        'res.partner', string="Student", domain=[('is_student', '=', True)])
    standard = fields.Many2one(related='student_id.standard', string='Standard')
    division = fields.Many2one(related='student_id.div', string='Division')
    roll_no = fields.Integer(related='student_id.roll_no', string="Roll No")
    emailid = fields.Char(related="student_id.email")
    book_limit = fields.Char('Issue Book Limit', size=1)
    start_date = fields.Date('Start Date', default=fields.Date.context_today)
    end_date = fields.Date('End Date')
    user = fields.Char("Default user", default=_get_default_user)
    state = fields.Selection([
        ('new', 'New'),
        ('active', 'Active'),
        ('expire', 'Expire')], default="new", string="Membership Status", readonly=True)

    @api.model_create_multi
    def create(self, vals):
        res = super(Memberships, self).create(vals)
        for memb_rec in res:
            memb_rec.memberships_code = self.env[
            'ir.sequence'].next_by_code('memberships.seq')
        return res

    def memberships_new(self):
        self.ensure_one()
        self.state = 'new'

    def memberships_active(self):
        self.ensure_one()
        self.state = 'active'

    def memberships_expire(self):
        self.ensure_one()
        self.state = 'expire'
