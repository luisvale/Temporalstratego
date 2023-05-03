# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
class ProjectProject(models.Model):
    _inherit = "project.project"

    note = fields.Text('Descripción')

    def action_view_so(self):
        self.ensure_one()
        action_window = {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "name": "Sales Order",
            "views": [[False, "form"]],
            "context": {"create": False, "show_sale": True},
            "res_id": self.sale_order_id.id
        }
        return action_window

class ProjectTask(models.Model):
    _inherit = "project.task"

    allowed_user_ids = fields.Many2many('res.users', string="Visible to", groups='project.group_project_manager,l10n_cr_stratego.group_project_manager_only',
                                        compute='_compute_allowed_user_ids', store=True, readonly=False, copy=False)


    #Todo: Solo para descripción del proyecto
    sol_product_id = fields.Many2one('product.product',string='Descripción',  compute='compute_fields_order_line', store=True)
    sol_description = fields.Char(string='Descripción',  compute='compute_fields_order_line', store=True)
    sol_qty = fields.Float(string='Cantidad Total', compute='compute_fields_order_line', store=True)
    sol_price_cost = fields.Float(string='Precio Costo',  compute='compute_fields_order_line', store=True)
    sol_new_qty = fields.Float(string='Cantidad',  compute='compute_fields_order_line', store=True)
    sol_pax_days_hours = fields.Float(string='Por pax/días/horas',  compute='compute_fields_order_line', store=True)
    sol_total = fields.Float(string='Total Costo', compute='compute_fields_order_line', store=True)

    @api.depends('sale_line_id','sale_line_id.price_cost','sale_line_id.product_uom_qty')
    def compute_fields_order_line(self):
        for task in self:
            if task.sale_line_id:
                sol = task.sale_line_id
                task.sol_product_id = sol.product_id
                task.sol_description = sol.name
                task.sol_qty = sol.product_uom_qty
                task.sol_price_cost = sol.price_cost
                task.sol_new_qty = sol.new_qty
                task.sol_pax_days_hours = sol.pax_days_hours
                task.sol_total = task.sol_qty * task.sol_price_cost

