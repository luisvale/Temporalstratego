# -*- coding: utf-8 -*-

import base64
import logging
from odoo import _, api, fields, models
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from collections import defaultdict
from odoo.tools import float_compare, date_utils, email_split, email_re
from odoo.tools.misc import formatLang, format_date, get_lang

class AccountMove(models.Model):
    _inherit = "account.move"

    cuenta_analitica_id = fields.Many2one(comodel_name="account.analytic.account", string="Cuenta analítica",compute='_compute_project')
    proyecto_id = fields.Many2one('project.project',string='Proyecto',compute='_compute_project')

    tipo_documento = fields.Selection(selection_add=[
        ('NN', 'No generar documento de hacienda')
    ], ondelete={'code': 'cascade'})

    @api.onchange('tipo_documento')
    def _onchange_tipo_documento(self):
        self._compute_to_process()

    @api.depends("company_id.frm_ws_ambiente", "journal_id.to_process")
    def _compute_to_process(self):
        for invoice in self:
            if invoice.tipo_documento == 'NN':
                invoice.to_process = False
            else:
                invoice.to_process = (invoice.company_id.frm_ws_ambiente and invoice.journal_id.to_process)

    @api.depends('invoice_origin')
    def _compute_project(self):
        for inv in self:
            if inv.move_type == 'out_invoice' and inv.invoice_origin:
                order = self.env['sale.order'].sudo().search([('name','=',inv.invoice_origin)],limit=1)
                if order:
                    inv.cuenta_analitica_id = order.analytic_account_id
                    inv.proyecto_id = order.project_id
            else:
                inv.cuenta_analitica_id = False
                inv.proyecto_id = False


    def action_invoice_sent(self):
        """ Open a window to compose an email, with the edi invoice template
            message loaded by default
        """
        self.ensure_one()
        template = self.env.ref('account.email_template_edi_invoice', raise_if_not_found=False)
        lang = False
        if template:
            lang = template._render_lang(self.ids)[self.id]
        if not lang:
            lang = get_lang(self.env).code

        self._get_attach_einvoice(template)
        compose_form = self.env.ref('account.account_invoice_send_wizard_form', raise_if_not_found=False)
        ctx = dict(
            default_model='account.move',
            default_res_id=self.id,
            # For the sake of consistency we need a default_res_model if
            # default_res_id is set. Not renaming default_model as it can
            # create many side-effects.
            default_res_model='account.move',
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            default_composition_mode='comment',
            mark_invoice_as_sent=True,
            custom_layout="mail.mail_notification_paynow",
            model_description=self.with_context(lang=lang).type_name,
            force_email=True
        )
        return {
            'name': _('Send Invoice'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice.send',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    #Todo: Traer attachments de facturación
    def _get_attach_einvoice(self, email_template):
        if self.partner_id and self.partner_id.email:
            attachment_search = (
                self.env["ir.attachment"]
                    .sudo()
                    .search_read(
                    [
                        ("res_model", "=", "account.move"),
                        ("res_id", "=", self.id),
                        ("res_field", "=", "xml_comprobante"),
                    ],
                    limit=1,
                )
            )
            if attachment_search:
                attachment = self.env["ir.attachment"].browse(attachment_search[0]["id"])
                attachment.name = self.fname_xml_comprobante

                attachment_resp_search = (
                    self.env["ir.attachment"]
                        .sudo()
                        .search_read(
                        [
                            ("res_model", "=", "account.move"),
                            ("res_id", "=", self.id),
                            ("res_field", "=", "xml_respuesta_tributacion"),
                        ],
                        limit=1,
                    )
                )

                if attachment_resp_search:
                    attachment_resp = self.env["ir.attachment"].browse(
                        attachment_resp_search[0]["id"]
                    )
                    attachment_resp.name = self.fname_xml_respuesta_tributacion

                    email_template.attachment_ids = [(6, 0, [attachment.id, attachment_resp.id])]

    # def _post(self, soft=True):
    #     """Post/Validate the documents.
    #
    #     Posting the documents will give it a number, and check that the document is
    #     complete (some fields might not be required if not posted but are required
    #     otherwise).
    #     If the journal is locked with a hash table, it will be impossible to change
    #     some fields afterwards.
    #
    #     :param soft (bool): if True, future documents are not immediately posted,
    #         but are set to be auto posted automatically at the set accounting date.
    #         Nothing will be performed on those documents before the accounting date.
    #     :return Model<account.move>: the documents that have been posted
    #     """
    #     if soft:
    #         future_moves = self.filtered(lambda move: move.date > fields.Date.context_today(self))
    #         future_moves.auto_post = True
    #         for move in future_moves:
    #             msg = _('This move will be posted at the accounting date: %(date)s', date=format_date(self.env, move.date))
    #             move.message_post(body=msg)
    #         to_post = self - future_moves
    #     else:
    #         to_post = self
    #
    #     # `user_has_group` won't be bypassed by `sudo()` since it doesn't change the user anymore.
    #     #Agregado de grupos de usuario
    #     if not self.env.su and not self._evalue_access_post_invoice(self.env.user):
    #         raise AccessError(_("You don't have the access rights to post an invoice."))
    #     for move in to_post:
    #         if move.state == 'posted':
    #             raise UserError(_('The entry %s (id %s) is already posted.') % (move.name, move.id))
    #         if not move.line_ids.filtered(lambda line: not line.display_type):
    #             raise UserError(_('You need to add a line before posting.'))
    #         if move.auto_post and move.date > fields.Date.context_today(self):
    #             date_msg = move.date.strftime(get_lang(self.env).date_format)
    #             raise UserError(_("This move is configured to be auto-posted on %s", date_msg))
    #
    #         if not move.partner_id:
    #             if move.is_sale_document():
    #                 raise UserError(_("The field 'Customer' is required, please complete it to validate the Customer Invoice."))
    #             elif move.is_purchase_document():
    #                 raise UserError(_("The field 'Vendor' is required, please complete it to validate the Vendor Bill."))
    #
    #         if move.is_invoice(include_receipts=True) and float_compare(move.amount_total, 0.0, precision_rounding=move.currency_id.rounding) < 0:
    #             raise UserError(_("You cannot validate an invoice with a negative total amount. You should create a credit note instead. Use the action menu to transform it into a credit note or refund."))
    #
    #         # Handle case when the invoice_date is not set. In that case, the invoice_date is set at today and then,
    #         # lines are recomputed accordingly.
    #         # /!\ 'check_move_validity' must be there since the dynamic lines will be recomputed outside the 'onchange'
    #         # environment.
    #         if not move.invoice_date:
    #             if move.is_sale_document(include_receipts=True):
    #                 move.invoice_date = fields.Date.context_today(self)
    #                 move.with_context(check_move_validity=False)._onchange_invoice_date()
    #             elif move.is_purchase_document(include_receipts=True):
    #                 raise UserError(_("The Bill/Refund date is required to validate this document."))
    #
    #         # When the accounting date is prior to the tax lock date, move it automatically to the next available date.
    #         # /!\ 'check_move_validity' must be there since the dynamic lines will be recomputed outside the 'onchange'
    #         # environment.
    #         if (move.company_id.tax_lock_date and move.date <= move.company_id.tax_lock_date) and (move.line_ids.tax_ids or move.line_ids.tax_tag_ids):
    #             move.date = move._get_accounting_date(move.invoice_date or move.date, True)
    #             move.with_context(check_move_validity=False)._onchange_currency()
    #
    #     # Create the analytic lines in batch is faster as it leads to less cache invalidation.
    #     to_post.mapped('line_ids').create_analytic_lines()
    #     to_post.write({
    #         'state': 'posted',
    #         'posted_before': True,
    #     })
    #
    #     for move in to_post:
    #         move.message_subscribe([p.id for p in [move.partner_id] if p not in move.sudo().message_partner_ids])
    #
    #         # Compute 'ref' for 'out_invoice'.
    #         if move._auto_compute_invoice_reference():
    #             to_write = {
    #                 'payment_reference': move._get_invoice_computed_reference(),
    #                 'line_ids': []
    #             }
    #             for line in move.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable')):
    #                 to_write['line_ids'].append((1, line.id, {'name': to_write['payment_reference']}))
    #             move.write(to_write)
    #
    #     for move in to_post:
    #         if move.is_sale_document() \
    #                 and move.journal_id.sale_activity_type_id \
    #                 and (move.journal_id.sale_activity_user_id or move.invoice_user_id).id not in (self.env.ref('base.user_root').id, False):
    #             move.activity_schedule(
    #                 date_deadline=min((date for date in move.line_ids.mapped('date_maturity') if date), default=move.date),
    #                 activity_type_id=move.journal_id.sale_activity_type_id.id,
    #                 summary=move.journal_id.sale_activity_note,
    #                 user_id=move.journal_id.sale_activity_user_id.id or move.invoice_user_id.id,
    #             )
    #
    #     customer_count, supplier_count = defaultdict(int), defaultdict(int)
    #     for move in to_post:
    #         if move.is_sale_document():
    #             customer_count[move.partner_id] += 1
    #         elif move.is_purchase_document():
    #             supplier_count[move.partner_id] += 1
    #     for partner, count in customer_count.items():
    #         (partner | partner.commercial_partner_id)._increase_rank('customer_rank', count)
    #     for partner, count in supplier_count.items():
    #         (partner | partner.commercial_partner_id)._increase_rank('supplier_rank', count)
    #
    #     # Trigger action for paid invoices in amount is zero
    #     to_post.filtered(
    #         lambda m: m.is_invoice(include_receipts=True) and m.currency_id.is_zero(m.amount_total)
    #     ).action_invoice_paid()
    #
    #     # Force balance check since nothing prevents another module to create an incorrect entry.
    #     # This is performed at the very end to avoid flushing fields before the whole processing.
    #     to_post._check_balanced()
    #     return to_post
    #
    #
    # def _evalue_access_post_invoice(self,user):
    #     res = False
    #     if user.has_group('account.group_account_invoice') \
    #             or user.has_group('l10n_cr_stratego.group_account_invoice_supplier') \
    #             or user.has_group('l10n_cr_stratego.group_account_invoice_supplier_paids'):
    #         res = True
    #
    #
    #     return res



