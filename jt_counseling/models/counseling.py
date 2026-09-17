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

from odoo import fields, models, api, _
from odoo.exceptions import RedirectWarning

class StudentCounseling(models.Model):
    _name = 'student.counseling'
    _description = "Student Counseling"
    _inherit = [
                'mail.thread',
                'mail.activity.mixin',
               ]
    _rec_name = "student_id"

    student_id = fields.Many2one('res.partner', string="Student", domain=[('is_student', '=', True)])
    faculty_id = fields.Many2one('res.partner', string="Faculty", domain=[('is_faculty', '=', True)])
    note = fields.Text(string='Note')
    timer_start = fields.Datetime(string='Timer Start')
    timer_pause = fields.Datetime(string='Last Pause Time')
    timer_stop = fields.Datetime(string='Timer Stop')
    timer_state = fields.Selection([
        ('not_started', 'Not Started'),
        ('running', 'On Going'),
        ('paused', 'Paused'),
        ('stopped', 'Completed'),
    ], string='Timer State', default='not_started')
    total_time = fields.Char(string='Total Time (in hours)', compute='_compute_total_time', store=True)
    survey_link = fields.Char(string='Survey Link')
    cids = fields.Integer()
    menu_id = fields.Integer()
    action_id = fields.Integer()

    def open_link(self):

        survey_link = self.survey_link
        
        if not survey_link:
            action = self.env.ref('jt_counseling.action_student_counseling')
            raise RedirectWarning(_('Survey link is not configured.'), action.id, _('Enter Link'))
        action = self.env.ref('jt_counseling.action_student_counseling')
        menu_id = self.env.ref('jt_counseling.student_counseling_submenu')
        url = survey_link + "/%s/%s/%s" % (self.id, action.id, menu_id.id)
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    def action_timer_start(self):
        if self.timer_state == 'not_started':
            self.timer_start = fields.Datetime.now()
            self.timer_state = 'running'
        elif self.timer_state == 'paused':
            total_paused_time = fields.Datetime.from_string(fields.Datetime.now()) - fields.Datetime.from_string(self.timer_pause)
            self.timer_start += total_paused_time
            self.timer_state = 'running'

    def action_timer_pause(self):
        if self.timer_state == 'running':
            self.write({'timer_pause': fields.Datetime.now(),
                        'timer_state':'paused'})

    def action_timer_resume(self):
        if self.timer_start and self.timer_pause and self.timer_state == 'paused':
            new_start = self.timer_start + (fields.Datetime.now() - self.timer_pause)
            self.write({'timer_start': new_start, 
                        'timer_pause': False,
                        'timer_state':'running'})
    
    def action_timer_stop(self):
        if self.timer_state in ['running', 'paused']:

            self.write({"timer_stop":fields.Datetime.now(),
                        "timer_state": 'stopped'})


    @api.depends('timer_start', 'timer_pause', 'timer_stop', 'timer_state')
    def _compute_total_time(self):
        for task in self:
            total_time = 0.0
            task.total_time = '00:00:00'
            if task.timer_start:
                start_time = fields.Datetime.from_string(task.timer_start)  
                if task.timer_state == 'running':
                    total_time = (fields.Datetime.now() - start_time).total_seconds() 
                elif task.timer_state == 'paused' and task.timer_pause:
                    pause_time = fields.Datetime.from_string(task.timer_pause)
                    total_time = (pause_time - start_time).total_seconds() 
                elif task.timer_state == 'stopped':
                    if task.timer_pause:
                        pause_time = fields.Datetime.from_string(task.timer_pause)
                        total_time = (pause_time - start_time).total_seconds() 
                    else :
                        stop_time = fields.Datetime.from_string(task.timer_stop)
                        total_time = (stop_time - start_time).total_seconds() 

                seconds = total_time % (24 * 3600)
                hour = seconds // 3600
                seconds %= 3600
                minutes = seconds // 60
                seconds %= 60
                
                time_spent ='%02d:%02d:%02d' % (hour, minutes, seconds)
                task.total_time = str(time_spent)


    # def generate_url(self):
    #     detail = self.env.context.get('params')
    #     print("detail----->>>>",detail)
    #     base_url = 'http://localhost:8088/web'
    #     fragment_params = {
    #         'id': detail.get('id') if detail.get('id') else '',
    #         'cids': 1,
    #         'menu_id': detail.get('menu_id') if detail.get('menu_id') else '',
    #         'action': detail.get('action') if detail.get('action') else '',
    #         'model': 'student.counseling',
    #         'view_type': 'form',
    #     }

    #     fragment = '#' + url_encode(fragment_params)
    #     url = url_join(base_url, '?' + url_encode(detail) + fragment)
    #     print("url---->>>>",url)
    #     return {
    #             'type': 'ir.actions.act_url',
    #             'url': url,
    #             'target': 'self',
    #         }


    
class StudentSurvey(models.Model):
    _inherit = 'survey.survey'

    is_counseling = fields.Boolean(string='Is Counselling')