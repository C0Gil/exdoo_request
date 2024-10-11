# -*- coding:utf-8 -*-

from odoo import models, fields

class ExdooRequestSale(models.Model):
    _inherit = ['sale.order']
    
    exdoo_request_id = fields.Many2one(comodel_name="exdoo.request", string="ids_exdoo_request") 
    
    
    def _create_invoices(self, grouped=False, final=False):        
        invoices = super(ExdooRequestSale, self)._create_invoices(grouped=grouped, final=final)

        # Transferir el request_id de la venta a la factura
        for invoice in invoices:
            invoice.exdoo_request_id = self.exdoo_request_id

        return invoices