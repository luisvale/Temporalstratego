import base64
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime

from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import email_re, email_split

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    state_email = fields.Selection(
        selection=[
            ("no_email", _("No email account")),
            ("sent", _("Sent")),
            ("fe_error", _("Error FE")),
        ],
        copy=False,
    )

    def name_get(self):
        """
        - Add amount_untaxed in name_get of invoices
        - Skipp number usage on invoice from incoming mail
        """
        if self._context.get("invoice_from_incoming_mail"):
            logging.info("Factura de correo")
            res = []
            for inv in self:
                res.append((inv.id, (inv.name or str(inv.id)) + "MI"))
            return res
        res = super(AccountMove, self).name_get()
        if self._context.get("invoice_show_amount"):
            new_res = []
            for (inv_id, name) in res:
                inv = self.browse(inv_id)
                name += _(" Amount w/o tax: {} {}").format(inv.amount_untaxed, inv.currency_id.name)
                new_res.append((inv_id, name))
            return new_res
        else:
            return res


    def load_xml_data(self):
        pass
