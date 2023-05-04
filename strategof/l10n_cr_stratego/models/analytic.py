# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    show_not_cost = fields.Boolean(groups="l10n_cr_stratego.group_analytic_stratego_no_show", store=True)
    show_cost_revenue = fields.Boolean(compute='compute_show_not_cost', store=True)

    @api.depends('show_not_cost')
    def compute_show_not_cost(self):
        for record in self:
            record.show_cost_revenue = record.show_not_cost
