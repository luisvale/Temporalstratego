# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Importar facturas de proveedores desde un correo-e",
    "version": "12.0.1.0.3",
    "category": "Facturas de proveedor",
    "author": "JHONNY MERINO SAMILLÁN, CHICLAYO - PERÚ",
    "license": "AGPL-3",
    "website": "http://www.xalachi.com/",
    "summary": "Ninguno",
    "description": """
        Éste es un módulo modificado
    """,
    # any module necessary for this one to work correctly
    "depends": ["fecr"],
    # always loaded
    "data": [
        # 'security/ir.model.access.csv',
        "views/res_company_views.xml",
        "views/account_view.xml",
        "views/account_invoice_view.xml",
        "wizard/cr_multiple_invoice_validation_wz_view.xml",
    ],
}
