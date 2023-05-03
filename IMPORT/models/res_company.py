from odoo import fields, models, _, api


class CompanyElectronic(models.Model):
    _name = "res.company"
    _inherit = [
        "res.company",
        "mail.thread",
    ]

    @api.model
    def _get_default_company_id(self):
        c =  self._context.get('force_company', self.env.user.company_id.id)
        if c>0:
            company_id = self.env['res.company'].browse(c)
            return company_id
        else:
            return c

    company_id = fields.Many2one('res.company', string='Company',
        default=_get_default_company_id, required=True)


    def _get_default_journal_id(self):
        return self.env["account.journal"].search([("type", "=", "purchase")], limit=1)

    # Fields for automatic import invoice from email
    import_bill_automatic = fields.Boolean(
        string="Import Vendor Bills", help="Select to upload vendor bills from incoming email"
    )
    import_bill_mail_server_id = fields.Many2one(
        "fetchmail.server", string="Mail Server", help="Select the Incoming Mail Server"
    )
    #company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    import_bill_journal_id = fields.Many2one(
        string="Journal",
        comodel_name="account.journal",
        help="Vendor Bills Journal",
    )
    import_bill_product_id = fields.Many2one(
        "product.product",
        string="Product",
        help="Set a product to each line",
    )
    import_bill_account_id = fields.Many2one(
        "account.account",
        string="Expense Account",
        help="Assign a spending account to each line",
    )
    import_bill_account_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic Account",
        help="Assign an analytical account to each line",
    )

    @api.onchange("import_bill_automatic")
    def _import_bill_automatic(self):
        if self.import_bill_automatic:
            company  = self._get_default_company_id()
            self.company_id = company
        else:
            self.company_id = False
            self.clean_fields()


    @api.onchange("company_id")
    def _company_id(self):
        self.clean_fields()



    def clean_fields(self):
        self.import_bill_account_id = False
        self.import_bill_journal_id = False
        self.import_bill_product_id = False
        self.import_bill_account_analytic_id = False