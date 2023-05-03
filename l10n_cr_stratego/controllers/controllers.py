# -*- coding: utf-8 -*-
# from odoo import http


# class L10nCrStatego(http.Controller):
#     @http.route('/l10n_cr_statego/l10n_cr_statego/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/l10n_cr_statego/l10n_cr_statego/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('l10n_cr_statego.listing', {
#             'root': '/l10n_cr_statego/l10n_cr_statego',
#             'objects': http.request.env['l10n_cr_statego.l10n_cr_statego'].search([]),
#         })

#     @http.route('/l10n_cr_statego/l10n_cr_statego/objects/<model("l10n_cr_statego.l10n_cr_statego"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('l10n_cr_statego.object', {
#             'object': obj
#         })
