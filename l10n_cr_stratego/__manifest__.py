# -*- coding: utf-8 -*-
{
    'name': "Módulo STRATEGO",

    'summary': """
        Éste módulo contiene todos los cambios necesarios y personalizados para la empresa STRATEGO""",

    'description': """
        Módulo personalizado Stratego
    """,

    'author': "Odoomatic.com",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Theme/Services',
    'version': '14.0.2.6',

    # any module necessary for this one to work correctly
    'depends': ['base','account','sale_project','sale_account_project_inherits','l10n_cr_electronic_invoice','l10n_cr_accounting','sales_team','sale','analytic'],
    'license': 'LGPL-3',
    # always loaded
    'data': [
        #'security/ir.model.access.csv',
        'security/groups_customers.xml',
        'data/mail_data.xml',
        'data/groups.xml',
        'reports/account_move_new.xml',
        'views/product_views.xml',
        'views/sale_order_views.xml',
        'views/project_views.xml',
        'views/account_move_views.xml',
        #'views/electronic_invoice_views.xml',
        'views/access_group.xml',
        'views/account_journal_views.xml',
        'views/analytic_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
