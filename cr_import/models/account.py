# © 2011 Guewen Baconnier (Camptocamp)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).-
from odoo import models, fields


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    from_mail = fields.Boolean(
        'Desde email',
        help="If flagged, some fields of the invoice "
             "they will be read only ")

    has_ack = fields.Boolean(
        'Tiene ACK?',
        help="If flagged, indicates you have the "
             "answer (ACK) attached ")

    iva_condition = fields.Selection([
        ('gecr', 'Generate IVA credit'),
        ('crpa', 'Generates partial IVA credit'),
        ('bica', 'Capital assets'),
        ('gcnc', 'Current spending does not generate credit'),
        ('prop', 'Proportionality')],
        string='IVA Condition',
        required=False,
        default='gecr',
    )

    company_activity_id = fields.Many2one("economic.activity", string="Default economic activity", required=False,
                                  context={'active_test': False})
