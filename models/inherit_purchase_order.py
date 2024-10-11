# -*- coding:utf-8 -*-

from odoo import models, fields

class ExdooRequestPurchase(models.Model):
    _inherit = ['purchase.order']
    
    exdoo_request_id = fields.Many2one(comodel_name="exdoo.request", string="ids_exdoo_request") 