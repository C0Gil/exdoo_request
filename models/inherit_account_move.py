# -*- coding:utf-8 -*-

from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    # Relación con la solicitud
    exdoo_request_id = fields.Many2one('exdoo.request', string="Solicitud Relacionada")
