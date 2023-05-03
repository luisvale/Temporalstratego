# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def _prepare_invoice_values(self, order, name, amount, so_line):
        invoice_vals = super(SaleAdvancePaymentInv, self)._prepare_invoice_values()
        if order.apply_discount_global and order.percentage_discount_global > 0.0:
            invoice_vals = {}
            invoice_vals = {
                'ref': order.client_order_ref,
                'move_type': 'out_invoice',
                'invoice_origin': order.name,
                'invoice_user_id': order.user_id.id,
                'narration': order.note,
                'partner_id': order.partner_invoice_id.id,
                'fiscal_position_id': (order.fiscal_position_id or order.fiscal_position_id.get_fiscal_position(
                    order.partner_id.id)).id,
                'partner_shipping_id': order.partner_shipping_id.id,
                'currency_id': order.pricelist_id.currency_id.id,
                'payment_reference': order.reference,
                'invoice_payment_term_id': order.payment_term_id.id,
                'partner_bank_id': order.company_id.partner_id.bank_ids[:1].id,
                'team_id': order.team_id.id,
                'campaign_id': order.campaign_id.id,
                'medium_id': order.medium_id.id,
                'source_id': order.source_id.id,
                'apply_discount_global': order.apply_discount_global,
                'percentage_discount_global': order.percentage_discount_global,
                'invoice_line_ids': [(0, 0, {
                    'name': name,
                    'price_unit': amount,
                    'quantity': 1.0,
                    'discount': so_line.discount,
                    'product_id': self.product_id.id,
                    'product_uom_id': so_line.product_uom.id,
                    'tax_ids': [(6, 0, so_line.tax_id.ids)],
                    'sale_line_ids': [(6, 0, [so_line.id])],
                    'analytic_tag_ids': [(6, 0, so_line.analytic_tag_ids.ids)],
                    'analytic_account_id': order.analytic_account_id.id or False,
                })],
            }

        return invoice_vals
