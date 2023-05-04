# -*- coding: utf-8 -*-
from lxml import etree

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    available_partner_bank_ids = fields.Many2many(
        comodel_name='res.partner.bank',
        compute='_compute_available_partner_bank_ids',
    )

    @api.depends('can_edit_wizard', 'journal_id')
    def _compute_available_partner_bank_ids(self):
        for wizard in self:
            if wizard.can_edit_wizard:
                batch = wizard._get_batches()[0]
                wizard.available_partner_bank_ids = wizard._get_batch_available_partner_banks(batch, wizard.journal_id)
            else:
                wizard.available_partner_bank_ids = None

    @api.model
    def _get_batch_available_partner_banks(self, batch_result, journal):
        key_values = batch_result['key_values']
        company = batch_result['lines'].company_id

        # A specific bank account is set on the journal. The user must use this one.
        if key_values['payment_type'] == 'inbound':
            # Receiving money on a bank account linked to the journal.
            return journal.bank_account_id
        else:
            # Sending money to a bank account owned by a partner.
            return batch_result['lines'].partner_id.bank_ids.filtered(lambda x: x.company_id.id in (False, company.id))._origin