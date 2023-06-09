# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountInvoiceImportConfig(models.Model):
    _name = "account.invoice.import.config"
    _description = "Configuracion para importar Facturas de Proveedor"
    _order = "sequence"

    name = fields.Char(string=u"Descripción")
    company_id = fields.Many2one(comodel_name="res.company",string=u"Compañia",ondelete="cascade",
        default=lambda self: self.env["res.company"]._company_default_get('account.invoice.import.config'))
    partner_id = fields.Many2one(comodel_name="res.partner",store=True,related='company_id.partner_id',string='Contacto')
    active = fields.Boolean(string="Activo?",default=True)
    journal_id = fields.Many2one('account.journal',string='Diario proveedor')
    sequence = fields.Integer()
    invoice_line_method = fields.Selection(
        selection=[
            ("1line_no_product", _("Linea sin producto")),
            ("1line_static_product", _("Single Line, Static Product")),
            ("nline_no_product", _("Multi Line, No Product")),
            ("nline_static_product", _("Multi Line, Static Product")),
            ("nline_auto_product", _("Multi Line, Auto-selected Product")),
        ],
        string="Method for Invoice Line",
        default="1line_no_product",
        help="The multi-line methods will not work for PDF invoices "
        "that don't have an embedded XML file. "
        "The 'Multi Line, Auto-selected Product' method will only work with "
        "ZUGFeRD invoices at Comfort or Extended level, not at Basic level.",
    )

    account_id = fields.Many2one(comodel_name="account.account",string="Cuenta de gasto",domain=[("deprecated", "=", False),])
    account_analytic_id = fields.Many2one(comodel_name="account.analytic.account",string=u'Cuenta analítica')
    label = fields.Char(string="Force Description",help="Force supplier invoice line description")
    tax_ids = fields.Many2many(comodel_name="account.tax",string="Impuesto",domain=[("type_tax_use", "=", "purchase"),])
    static_product_id = fields.Many2one(comodel_name="product.product",string="Static Product")

    @api.constrains("invoice_line_method", "account_id", "static_product_id")
    def _check_import_config(self):
        for config in self:
            if "static_product" in config.invoice_line_method and not config.static_product_id:
                raise ValidationError(
                    _(
                        "Static Product must be set on the invoice import "
                        "configuration of supplier '{}' that has a Method "
                        "for Invoice Line set to 'Single Line, Static Product' "
                        "or 'Multi Line, Static Product'."
                    ).format(config.partner_id.name)
                )
            if "no_product" in config.invoice_line_method and not config.account_id:
                raise ValidationError(
                    _(
                        "The Expense Account must be set on the invoice "
                        "import configuration of supplier '{}' that has a "
                        "Method for Invoice Line set to 'Single Line, No Product' "
                        "or 'Multi Line, No Product'."
                    ).format(config.partner_id.name)
                )

    @api.onchange("invoice_line_method", "account_id")
    def invoice_line_method_change(self):
        if self.invoice_line_method == "1line_no_product" and self.account_id:
            self.tax_ids = [(6, 0, self.account_id.tax_ids.ids)]
        elif self.invoice_line_method != "1line_no_product":
            self.tax_ids = [(6, 0, [])]

    def convert_to_import_config(self):
        self.ensure_one()
        vals = {
            "invoice_line_method": self.invoice_line_method,
            "account_analytic": self.account_analytic_id or False,
        }
        if self.invoice_line_method == "1line_no_product":
            vals["account"] = self.account_id
            vals["taxes"] = self.tax_ids
            vals["label"] = self.label or False
        elif self.invoice_line_method == "1line_static_product":
            vals["product"] = self.static_product_id
            vals["label"] = self.label or False
        elif self.invoice_line_method == "nline_no_product":
            vals["account"] = self.account_id
        elif self.invoice_line_method == "nline_static_product":
            vals["product"] = self.static_product_id
        return vals
