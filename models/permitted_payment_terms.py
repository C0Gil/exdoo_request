# -*- coding:utf-8 -*-

from odoo import models, fields, api

class PrmttdPaymentTermns(models.Model):
    _inherit = ['res.partner']
    
    payment_term_domain = fields.Many2many(
        comodel_name="account.payment.term",
        string="Dominio de términos de pago",
        compute="_compute_payment_term_domain",
        store=False
    )
    
    permitted_payment_terms = fields.Many2many(
        comodel_name="account.payment.term",
        string="Términos de pago permitidos",
        domain="[('company_id', 'in', [current_company_id, False])]"
    )
    
    property_payment_term_id = fields.Many2one(
        domain="[('id', 'in', payment_term_domain)]",
    )
      
    @api.depends('permitted_payment_terms')
    def _compute_payment_term_domain(self):
        for record in self:
            if record.permitted_payment_terms:
                record.payment_term_domain = record.permitted_payment_terms
            else:
                record.payment_term_domain = False