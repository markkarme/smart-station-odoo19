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


class AssignmentStudent(models.Model):
    _inherit = "res.partner"
    # _description = "Assignment Student Class"

    allocation_ids = fields.Many2many('student.assignment', string='Assignment(s)')
    assignment_count = fields.Integer(compute='compute_count_assignment')

    def get_assignment(self):
        action = self.env.ref('jt_education_assignment.'
                              'action_student_assignment').read()[0]
        action['domain'] = [('allocation_ids', 'in', self.ids), ('state', '=', 'publish')]
        return action

    def compute_count_assignment(self):
        for record in self:
            record.assignment_count = self.env['student.assignment'].search_count(
                [('allocation_ids', '=', self.id), ('state', '=', 'publish')])


class ResUsers(models.Model):
    _inherit = 'res.users'

    is_student = fields.Boolean(string='Is Student', compute='_compute_is_student_and_is_parent')
    is_parent = fields.Boolean(string='Is Parent', compute='_compute_is_student_and_is_parent')

    @api.depends('partner_id')
    def _compute_is_student_and_is_parent(self):
        for user in self:
            if user.partner_id:
                user.is_student = user.partner_id.is_student
                user.is_parent = user.partner_id.is_parent
            else:
                user.is_student = False
                user.is_parent = False 