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
from odoo import http
from odoo.exceptions import UserError
from odoo.http import request
from werkzeug.urls import url_join, url_encode
from odoo.addons.survey.controllers.main import Survey


class CounselingSurvey(Survey):

    @http.route([
        '/survey/start/<string:survey_token>',
        '/survey/start/<string:survey_token>/<int:cn_id>/<int:cn_ac_id>/<int:cn_mn_id>',
    ], type='http', auth='public', website=True)
    def survey_start(self, survey_token, answer_token=None, cn_id=None, cn_ac_id=None, cn_mn_id=None, email=False, **post):
        if not (cn_id and cn_ac_id and cn_mn_id):
            return super().survey_start(survey_token, answer_token=answer_token, email=email, **post)

        answer_from_cookie = False
        if not answer_token:
            answer_token = request.cookies.get('survey_%s' % survey_token)
            answer_from_cookie = bool(answer_token)

        access_data = self._get_access_data(survey_token, answer_token, ensure_token=False)

        if answer_from_cookie and access_data['validity_code'] in ('answer_wrong_user', 'token_wrong'):
            access_data = self._get_access_data(survey_token, None, ensure_token=False)

        if access_data['validity_code'] is not True:
            return self._redirect_with_error(access_data, access_data['validity_code'])

        survey_sudo, answer_sudo = access_data['survey_sudo'], access_data['answer_sudo']
        if not answer_sudo:
            try:
                answer_sudo = survey_sudo._create_answer(user=request.env.user, email=email)
            except UserError:
                answer_sudo = False

        if not answer_sudo:
            try:
                survey_sudo.with_user(request.env.user).check_access('read')
            except Exception:
                return request.redirect("/")
            else:
                return request.render("survey.survey_403_page", {'survey': survey_sudo})

        lang = self._get_lang_with_fallback(answer_sudo.sudo(False))
        response = request.redirect(self.env['ir.http']._url_for(
            f'/survey/{survey_sudo.access_token}/{answer_sudo.access_token}/{cn_id}/{cn_ac_id}/{cn_mn_id}',
            lang.code,
        ))
        response.set_cookie(f'survey_{survey_sudo.access_token}', answer_sudo.access_token, max_age=60 * 60 * 24)
        return response

    @http.route([
        '/survey/<string:survey_token>',
        '/survey/<string:survey_token>/<string:answer_token>',
        '/survey/<string:survey_token>/<string:answer_token>/<int:cn_id>/<int:cn_mn_id>/<int:cn_ac_id>',
    ], type='http', auth='public', website=True)
    def survey_display_page(self, survey_token, answer_token=None, cn_id=None, cn_ac_id=None, cn_mn_id=None, **post):
        return super().survey_display_page(survey_token, answer_token=answer_token, **post)


class CounselingController(http.Controller):

    @http.route('/student/counseling', type='http', auth='public', csrf=True, website=True)
    def url_return_view(self, **kwargs):
        base_url = request.httprequest.url_root + 'web'
        referer_url = request.httprequest.headers.get('Referer')
        action_id, menu_id, counselling_id = '', '', ''
        if referer_url:
            menu_id = referer_url.rstrip('/').split('/')[-1]
            action_id = referer_url.rstrip('/').split('/')[-2]
            counselling_id = referer_url.rstrip('/').split('/')[-3]
        fragment_params = {
            'view_type': 'form',
            'model': 'student.counseling',
            'id': counselling_id,
            'menu_id': menu_id,
            'action': action_id,
        }
        fragment = '#' + url_encode(fragment_params)
        url = url_join(base_url, '?' + fragment)
        return request.redirect(url)