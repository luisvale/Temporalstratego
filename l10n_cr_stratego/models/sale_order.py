# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

from odoo.tools.safe_eval import safe_eval
from odoo.tools.sql import column_exists, create_column


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    name_project = fields.Char(string='Nombre del Proyecto')
    visible_projecto = fields.Boolean('Proyecto visible', compute='_compute_visible_projecto', readonly=True)

    @api.depends('order_line.product_id.type')
    def _compute_visible_projecto(self):
        for order in self:
            order.visible_projecto = any(tipo == 'service' for tipo in order.order_line.mapped('product_id.type'))

    def action_confirm(self):
        if self.name_project:
            if not self.analytic_account_id:
                analytic_account_id = self.env['account.analytic.account'].create({
                    'name': self.name_project,
                    'code': self.name
                })
                self.analytic_account_id = analytic_account_id

            if not self.project_id:
                project_id = self.env['project.project'].create({
                    'name': self.name_project,
                    'analytic_account_id': analytic_account_id.id,
                    'partner_id': self.partner_id.id,
                    'description': self.note
                })

                self.project_id = project_id

            #Asignar cuenta analítica a proyecto por defecto
            if not self.project_id.analytic_account_id and self.analytic_account_id:
                self.project_id.analytic_account_id = self.analytic_account_id

            if not self.project_id.partner_id:
                self.project_id.partner_id = self.partner_id

            if self.note and not self.project_id.description:
                self.project_id.description = self.note

        res = super(SaleOrder, self).action_confirm()
        #self._send_quotation_mail()
        return res


    def _send_quotation_mail(self):
        email_act = self.action_quotation_send()
        email_ctx = email_act.get('context', {})
        self.with_context(**email_ctx).message_post_with_template(email_ctx.get('default_template_id'))

    #
    # cls.analytic_account_sale = cls.env['account.analytic.account'].create({
    #     'name': 'Project for selling timesheet - AA',
    #     'code': 'AA-2030'
    # })
    #
    # # Create projects
    # cls.project_global = cls.env['project.project'].create({
    #     'name': 'Global Project',
    #     'analytic_account_id': cls.analytic_account_sale.id,
    # })

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    #Todo: sobreescritura, modulo: sale_project
    def _timesheet_service_generation(self):
        """ For service lines, create the task or the project. If already exists, it simply links
            the existing one to the line.
            Note: If the SO was confirmed, cancelled, set to draft then confirmed, avoid creating a
            new project/task. This explains the searches on 'sale_line_id' on project/task. This also
            implied if so line of generated task has been modified, we may regenerate it.
        """
        so_line_task_global_project = self.filtered(lambda sol: sol.is_service and sol.product_id.service_tracking == 'task_global_project')
        so_line_new_project = self.filtered(lambda sol: sol.is_service and sol.product_id.service_tracking in ['project_only', 'task_in_project'])

        # search so lines from SO of current so lines having their project generated, in order to check if the current one can
        # create its own project, or reuse the one of its order.
        map_so_project = {}
        if so_line_new_project:
            order_ids = self.mapped('order_id').ids
            so_lines_with_project = self.search([('order_id', 'in', order_ids), ('project_id', '!=', False), ('product_id.service_tracking', 'in', ['project_only', 'task_in_project']), ('product_id.project_template_id', '=', False)])
            map_so_project = {sol.order_id.id: sol.project_id for sol in so_lines_with_project}
            so_lines_with_project_templates = self.search([('order_id', 'in', order_ids), ('project_id', '!=', False), ('product_id.service_tracking', 'in', ['project_only', 'task_in_project']), ('product_id.project_template_id', '!=', False)])
            map_so_project_templates = {(sol.order_id.id, sol.product_id.project_template_id.id): sol.project_id for sol in so_lines_with_project_templates}

        # search the global project of current SO lines, in which create their task
        map_sol_project = {}
        if so_line_task_global_project:
            map_sol_project = {sol.id: sol.product_id.with_company(sol.company_id).project_id for sol in so_line_task_global_project}

        def _can_create_project(sol):
            if not sol.project_id:
                if sol.product_id.project_template_id:
                    return (sol.order_id.id, sol.product_id.project_template_id.id) not in map_so_project_templates
                elif sol.order_id.id not in map_so_project:
                    return True
            return False

        def _determine_project(so_line):
            """Determine the project for this sale order line.
            Rules are different based on the service_tracking:

            - 'project_only': the project_id can only come from the sale order line itself
            - 'task_in_project': the project_id comes from the sale order line only if no project_id was configured
              on the parent sale order"""

            if so_line.product_id.service_tracking == 'project_only':
                return so_line.project_id
            elif so_line.product_id.service_tracking == 'task_in_project':
                return so_line.order_id.project_id or so_line.project_id
            elif so_line.order_id.project_id: #Nuevo
                return so_line.order_id.project_id

            return False

        # task_global_project: create task in global project
        for so_line in so_line_task_global_project:
            if not so_line.task_id:
                if map_sol_project.get(so_line.id):
                    so_line._timesheet_create_task(project=map_sol_project[so_line.id])

        # project_only, task_in_project: create a new project, based or not on a template (1 per SO). May be create a task too.
        # if 'task_in_project' and project_id configured on SO, use that one instead
        for so_line in so_line_new_project:
            project = _determine_project(so_line)
            if not project and _can_create_project(so_line):
                project = so_line._timesheet_create_project()
                if so_line.product_id.project_template_id:
                    map_so_project_templates[(so_line.order_id.id, so_line.product_id.project_template_id.id)] = project
                else:
                    map_so_project[so_line.order_id.id] = project
            elif not project:
                # Attach subsequent SO lines to the created project
                so_line.project_id = (
                    map_so_project_templates.get((so_line.order_id.id, so_line.product_id.project_template_id.id))
                    or map_so_project.get(so_line.order_id.id)
                )
            if so_line.product_id.service_tracking == 'task_in_project':
                if not project:
                    if so_line.product_id.project_template_id:
                        project = map_so_project_templates[(so_line.order_id.id, so_line.product_id.project_template_id.id)]
                    else:
                        project = map_so_project[so_line.order_id.id]
                if not so_line.task_id:
                    task = so_line._timesheet_create_task(project=project)
                    if task:
                        project.sale_order_id = so_line.order_id

    def _timesheet_create_task_prepare_values(self, project):
        self.ensure_one()
        planned_hours = self._convert_qty_company_hours(self.company_id)
        sale_line_name_parts = self.name.split('\n')
        title = sale_line_name_parts[0] or self.product_id.name
        #description = '<br/>'.join(sale_line_name_parts[1:])
        description = self.order_id.note

        return {
            'name': title if project.sale_line_id else '%s: %s' % (self.order_id.name or '', title),
            'planned_hours': planned_hours,
            'partner_id': self.order_id.partner_id.id,
            'email_from': self.order_id.partner_id.email,
            'description': description,
            'project_id': project.id, #Nuevo
            'sale_line_id': self.id,
            'sale_order_id': self.order_id.id,
            'company_id': project.company_id.id,
            'user_id': False,  # force non assigned task, as created as sudo()
        }

