# -*- coding: utf-8 -*-

from odoo import api,fields, models


class AccountConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    module_import_bills = fields.Boolean(string=u"Importación facturas electrónicas",
                                         implied_group='account.group_account_manager')
    invoice_import_ids = fields.Many2one(
        comodel_name="account.invoice.import.config",
        inverse_name="company_id",
        string=u'Configuración para importar facturas.'
    )

    def set_values(self):
        super(AccountConfigSettings, self).set_values()
        self.env['ir.config_parameter'].set_param('module_import_bills', self.module_import_bills)

    @api.model
    def get_values(self):
        res = super(AccountConfigSettings, self).get_values()
        res.update(module_import_bills=self.env['ir.config_parameter'].get_param('module_import_bills'))
        return res

    def open_params_import_ininvoice(self):
        id=None
        config = self.env['account.invoice.import.config'].sudo().search([('company_id','=',self.env.company.id),('active','=',True)])
        if config:
            id = config.id


        return {
            'type': 'ir.actions.act_window',
            'name': u'Configuración',
            'view_mode': 'form',
            'res_model': 'account.invoice.import.config',
            'res_id': id,
            'target': 'current',
            'context': {
                'default_company_id': self.env.company.id,
                'form_view_initial_mode': 'edit',
            }
        }
