# -*- coding:utf-8 -*-

from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    """ auto_purchase_on_confirm = fields.Boolean(
        string="Compra automática al confirmar solicitud",
        help="Permitir realizar la compra automáticamente al confirmar una solicitud"
    ) """

    """ def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('sale.auto_purchase_on_confirm', self.auto_purchase_on_confirm)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res['auto_purchase_on_confirm'] = self.env['ir.config_parameter'].sudo().get_param('sale.auto_purchase_on_confirm')
        return res
    """
    
    auto_purchase_on_confirm = fields.Boolean(
        string="Compra automática al confirmar",
        related="company_id.auto_purchase_on_confirm",
        readonly=False,
        help="Permite realizar la compra automática de productos faltantes al confirmar una solicitud.",        
    )

class ResCompany(models.Model):
    _inherit = 'res.company'

    auto_purchase_on_confirm = fields.Boolean(
        string="Compra automática al confirmar",
        help="Permite realizar la compra automática de productos faltantes al confirmar una solicitud.",        
    )