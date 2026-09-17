# -*- coding: utf-8 -*-
# from odoo import http


# class StudentManagementSystem(http.Controller):
#     @http.route('/student_management_system/student_management_system', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/student_management_system/student_management_system/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('student_management_system.listing', {
#             'root': '/student_management_system/student_management_system',
#             'objects': http.request.env['student_management_system.student_management_system'].search([]),
#         })

#     @http.route('/student_management_system/student_management_system/objects/<model("student_management_system.student_management_system"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('student_management_system.object', {
#             'object': obj
#         })

