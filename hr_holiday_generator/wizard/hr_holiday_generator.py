# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
from datetime import datetime, time

import dateutil
import requests
from odoo import _, fields, models
from odoo.exceptions import UserError


class HrHolidayGenerator(models.TransientModel):
    """This model is for creating a wizard and thus generating public holidays
    based on selected country."""
    _name = 'hr.holiday.generator'
    _description = 'Hr Holiday Generator'

    country_id = fields.Many2one("res.country", string="Country",
                                 help="Select your country from here",
                                 required=True)
    generation_mode = fields.Selection(
        [('year', 'YEAR'), ('month', 'MONTH'), ('date', 'DATE')],
        string="Date/Month/Year",
        help="Select date or month or year in which you want to get the public "
             "holidays", required=True)
    date = fields.Date(string="Date",
                       default=lambda self: fields.Date.today(),
                       help="Select the date you want to generate the public "
                            "holiday")
    month = fields.Selection([('1', 'January'),
                              ('2', 'February'),
                              ('3', 'March'),
                              ('4', 'April'),
                              ('5', 'May'),
                              ('6', 'June'),
                              ('7', 'July'),
                              ('8', 'August'),
                              ('9', 'September'),
                              ('10', 'October'),
                              ('11', 'November'),
                              ('12', 'December')], string="Month",
                             help="Select the month you want to generate the "
                                  "public holiday",
                             default=str(fields.Date.today().month))
    year = fields.Selection(
        selection='_get_years_selection',
        string="Year",
        help="Select the year you want to generate the public holiday",
        default=str(fields.Date.today().year))
    calender_leaves_ids = fields.One2many('calendar.leave',
                                          'holiday_generator_id',
                                          string="Calender leaves",
                                          help="The One2many field to take the "
                                               "values of the model "
                                               "calender_leave")

    def _get_years_selection(self):
        """This function is for getting years to select in the field year"""
        today = fields.Date.today()
        year_list = [(str(record), str(record)) for record in
                     range(today.year - 10, today.year + 10)]
        return year_list

    def _get_calendarific_language(self):
        """Map the current Odoo language to a Calendarific ISO639 code."""
        lang = self.env.lang or 'en_US'
        return 'ar' if lang.startswith('ar') else 'en'

    def _get_request_year(self):
        """Return the year used for the current generation request."""
        if self.generation_mode == 'date':
            return self.date.year
        return int(self.year)

    def _get_nager_local_names(self, country_code, year):
        """Fetch local-language holiday names from Nager.Date (free API).

        Calendarific's language parameter is premium-only and is ignored on
        free plans, so we enrich Arabic results with Nager.Date local names.
        """
        try:
            response = requests.get(
                f'https://date.nager.at/api/v3/PublicHolidays/{year}/{country_code}',
                timeout=10,
            )
            if response.status_code != 200:
                return {}
            return {
                holiday['date']: holiday.get('localName') or holiday['name']
                for holiday in response.json()
            }
        except requests.RequestException:
            return {}

    def _localize_holiday_name(self, holiday_date, default_name, local_names):
        """Return a localized holiday name when Arabic is requested."""
        if not local_names:
            return default_name
        return local_names.get(holiday_date.isoformat(), default_name)

    def _is_arabic_text(self, text):
        """Return True when the text already contains Arabic characters."""
        return bool(text) and any('\u0600' <= char <= '\u06FF' for char in text)

    def _translate_to_arabic(self, text, cache):
        """Translate English holiday text to Arabic using MyMemory API."""
        if not text or self._is_arabic_text(text):
            return text
        if text in cache:
            return cache[text]
        try:
            response = requests.get(
                'https://api.mymemory.translated.net/get',
                params={'q': text[:500], 'langpair': 'en|ar'},
                timeout=10,
            )
            if response.status_code == 200:
                translated = response.json().get(
                    'responseData', {}).get('translatedText', text)
                if translated and 'MYMEMORY WARNING' not in translated:
                    cache[text] = translated
                    return translated
        except requests.RequestException:
            pass
        cache[text] = text
        return text

    def _localize_holiday(self, holiday_date, name, description, local_names,
                          translation_cache):
        """Return Arabic name and description when Odoo language is Arabic."""
        if self._get_calendarific_language() != 'ar':
            return name, description
        localized_name = self._localize_holiday_name(
            holiday_date, name, local_names)
        localized_name = self._translate_to_arabic(
            localized_name, translation_cache)
        localized_description = self._translate_to_arabic(
            description, translation_cache)
        return localized_name, localized_description

    def action_generate(self):
        """This function is to set the action of button 'Generate'."""
        self.calender_leaves_ids = False
        api_key = self.env['ir.config_parameter'].sudo().get_param(
            'hr_holiday_generator.holiday_api_key') or False
        if api_key:
            base_url = "https://calendarific.com/api/v2/holidays"
            language = self._get_calendarific_language()
            url = (f"{base_url}?&api_key={api_key}&country="
                   f"{self.country_id.code}&language={language}")

            if self.generation_mode == 'year':
                url += f"&year={self.year}"
            elif self.generation_mode == 'month':
                url += f"&year={self.year}&month={self.month}"
            elif self.generation_mode == 'date':
                url += (f"&year={self.date.year}&month={self.date.month}"
                        f"&day={self.date.day}")
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                holidays_data = response.json()
                local_names = {}
                translation_cache = {}
                if language == 'ar':
                    local_names = self._get_nager_local_names(
                        self.country_id.code, self._get_request_year())
                calendar_leaves = []
                for holiday in holidays_data['response']['holidays']:
                    iso_datetime = holiday['date']['iso']
                    holiday_date = dateutil.parser.parse(iso_datetime).date()
                    start_datetime = datetime.combine(holiday_date, time.min)
                    end_datetime = datetime.combine(holiday_date, time.max)
                    holiday_name, holiday_description = self._localize_holiday(
                        holiday_date,
                        holiday['name'],
                        holiday.get('description') or '',
                        local_names,
                        translation_cache,
                    )
                    calendar_leaves.append(fields.Command.create({
                        'holiday_generator_id': self.id,
                        'name': holiday_name,
                        'start_date': start_datetime,
                        'end_date': end_datetime,
                        'description': holiday_description
                    }))
                self.calender_leaves_ids = calendar_leaves
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'hr.holiday.generator',
                'res_id': self.id,
                'view_mode': 'form',
                'view_id': self.env.ref(
                    'hr_holiday_generator.hr_holiday_generator_view_form').id,
                'target': 'new',
            }
        else:
            raise UserError(_(
                "To retrieve the data, kindly provide the API key in the "
                "general settings."))

    def action_save(self):
        """This function is to set the action of the button 'save'. """
        existing_holiday = self.env['resource.calendar.leaves'].search([
            ('resource_id', '=', False)])
        overlapping_dates = []
        overlapping_logs = []
        new_holiday_dates = []
        same_date_holidays = set()
        for existing in existing_holiday:
            for new_holiday in self.calender_leaves_ids:
                if existing.date_from.date() == \
                        new_holiday.start_date.date() or \
                        existing.date_to.date() == new_holiday.end_date.date():
                    overlapping_dates.append(new_holiday.start_date.date())
                    overlapping_logs.append({
                        'name': new_holiday.name,
                        'start_date': new_holiday.start_date,
                        'end_date': new_holiday.end_date,
                        'description': new_holiday.description
                    })
                    break
        for new_holiday in self.calender_leaves_ids:
            new_date = new_holiday.start_date.date()
            if new_date in new_holiday_dates:
                same_date_holidays.add(new_date)
            else:
                new_holiday_dates.append(new_date)
        for log in overlapping_logs:
            existing_logs = self.env['holiday.log'].search([
                ('name', '=', log['name']),
                ('start_date', '>=', log['start_date']),
                ('end_date', '<=', log['end_date'])
            ])
            if not existing_logs:
                self.env['holiday.log'].create(log)
        if overlapping_dates or same_date_holidays:
            warning_message = ""
            if overlapping_dates:
                existing_dates = ", ".join(
                    date.strftime('%Y-%m-%d') for date in overlapping_dates)
                warning_message += _(
                    "Public holidays already exist for the following date(s): "
                    "%s.\nPlease refer to the logs for detailed "
                    "information about the public holidays on these dates.\n\n"
                ) % existing_dates
            if same_date_holidays:
                warning_message += _("Select only one holiday per date:\n")
                warning_message += \
                    _("The following dates have multiple holidays:\n")
            for date in same_date_holidays:
                warning_message += f"\n- {date.strftime('%Y-%m-%d')}"
            warning = self.env['overlapping.date'].create(
                {'warning': warning_message})
            return {
                'name': _('Overlapping Dates Warning'),
                'type': 'ir.actions.act_window',
                'res_model': 'overlapping.date',
                'res_id': warning.id,
                'view_mode': 'form',
                'view_id': self.env.ref(
                    'hr_holiday_generator.overlapping_date_view_form').id,
                'target': 'new',
            }
        else:
            self.env['resource.calendar.leaves'].create([{
                'name': holiday.name,
                'date_from': holiday.start_date,
                'date_to': holiday.end_date
            } for holiday in self.calender_leaves_ids])
