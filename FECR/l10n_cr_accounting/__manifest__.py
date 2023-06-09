{
    "name": "L10N CR Accounting",
    "version": "14.0.0.2",
    "category": "Accounting",
    "author": "HomebrewSoft",
    "website": "https://homebrewsoft.dev",
    "license": "LGPL-3",
    "depends": [
        "account",
        "l10n_cr",
        "sale",
    ],
    "data": [
        # data
        "data/sale_conditions_data.xml",
        "data/account_payment_term.xml",
        "data/account_tax_data.xml",
        "data/code_type_product_data.xml",
        "data/economic_activity_data.xml",
        "data/payment_methods_data.xml",
        "data/reference_code_data.xml",
        # views
        "views/account_move_line.xml",
        # "views/account_invoice_tax.xml",
        "views/menu_views.xml",
        "views/account_move.xml",
        "views/account_payment_term.xml",
        "views/account_payment_views.xml",
        "views/account_tax_views.xml",
        "views/account_tax.xml",
        "views/code_type_product_views.xml",
        "views/product_template.xml",
        "views/res_company_views.xml",
        "views/sale_condition_views.xml",
    ],
}
