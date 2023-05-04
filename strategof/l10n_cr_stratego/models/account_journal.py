# -*- coding: utf-8 -*-

import base64
import logging
from odoo import _, api, fields, models
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError

ACCESS = [('project','Proyectos'),('admin','Administrativos')]

class AccountJournal(models.Model):
    _inherit = "account.journal"

    access_stratego = fields.Selection(ACCESS, string='Permisos en tablero')