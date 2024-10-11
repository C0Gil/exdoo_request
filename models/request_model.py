# -*- coding:utf-8 -*-
from collections import defaultdict

from odoo import models, fields, api

from odoo.exceptions import UserError


class ExdooRequest(models.Model):
    _name = 'exdoo.request'
    _description = "Exdoo Request"

    name = fields.Char(string="Nombre", copy=False, default="Nuevo")
    date = fields.Datetime(string="Fecha", copy=False, default=lambda self: fields.Datetime.now())
    approval_date = fields.Datetime(string="Fecha de confirmacion", copy=False)
    
    customer = fields.Many2one(comodel_name="res.partner", string="Cliente", required=True)    
    
    domain_payment_term = fields.Many2many(comodel_name="account.payment.term", string="Termino de pago dominio", related="customer.permitted_payment_terms")
    payment_term = fields.Many2one(comodel_name="account.payment.term", string="Termino de pago", domain="[('id', 'in', domain_payment_term)]")
    
    user = fields.Many2one(comodel_name="res.users", string="Usuario", default=lambda self: self.env.user )

    company_id = fields.Many2one(comodel_name="res.company", string="Compañia", default=lambda self: self.env.company)
    currency_id = fields.Many2one(comodel_name="res.currency", string="Moneda", default=lambda self: self.env.company.currency_id)    
    state = fields.Selection(selection=[
        ('borrador', 'Borrador'),
        ('confirmado', 'Confirmado'),
        ('cancelado', 'Cancelado'),
    ], default='borrador', string='Estados', copy=False)

    base = fields.Monetary(string='Subtotal', store=True, compute='_compute_amounts')
    taxes = fields.Monetary(string='Impuestos', store=True, compute='_compute_amounts')
    total = fields.Monetary(string='Total', store=True, compute='_compute_amounts')

    details_id = fields.One2many(comodel_name="request.details", inverse_name="id_request", string="ids_details")
    warehouse_id = fields.Many2one(comodel_name="stock.warehouse", string="Almacen")
    
    #sale_ids = fields.One2many('sale.order','exdoo_request_id',string="Ventas")
    sale_order_count = fields.Integer(string="Ventas", compute="_compute_sale_order_count")
    purchase_order_count = fields.Integer(string="Contador de Compras", compute="_compute_purchase_order_count")
    invoice_count = fields.Integer(string="Número de Facturas", compute='_compute_invoice_count')


    def confirm_request(self):
        self.state = 'confirmado'
        self.approval_date = fields.Datetime.now()
        self.create_sales()       

    def cancel_request(self):
        self.state = 'cancelado'

    def draft_request(self):
        self.state = 'borrador'    
    
    def create_sales(self):
        sale_order_obj = self.env['sale.order']
        sale_order_line_obj = self.env['sale.order.line']

        for request in self:

            sales_order_data = request._prepare_sales_order()
            sale_order = self.env['sale.order'].create(sales_order_data)
            sale_order_lines_data = request.action_confirm_request(sale_order.id)

            for line_data in sale_order_lines_data:
                self.env['sale.order.line'].create(line_data)
            
            sale_order.action_confirm()             
        
        return {
            'name': 'Venta',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': sale_order.id,
        }   
    
    def create_invoice(self):
        self.ensure_one()
        
        if not self.details_id:
            raise UserError("No hay productos en la solicitud para facturar.")
        
        invoice_vals = {
            'partner_id': self.customer.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [],
            'move_type': 'out_invoice',
            'exdoo_request_id': self.id,
        }
        
        for line in self.details_id:
            account_id = line.product_id.property_account_income_id.id or \
                     line.product_id.categ_id.property_account_income_categ_id.id
        
        for line in self.details_id:
            invoice_line_vals = {
                'product_id': line.product_id.id,
                'quantity': line.quantity,
                'price_unit': line.unit_price,
                'account_id': account_id,
                #'journal_id':
                'tax_ids': [(6, 0, line.tax_id.ids)],
            }
            invoice_vals['invoice_line_ids'].append((0, 0, invoice_line_vals))
        
        invoice = self.env['account.move'].create(invoice_vals)

        return {
            'name': 'Factura',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': invoice.id,
        }
            
    def _prepare_sales_order(self):        
        return {
            'partner_id': self.customer.id,
            'warehouse_id': self.warehouse_id.id,
            'exdoo_request_id': self.id,
        }

    def _compute_sale_order_count(self):
        for record in self:
            #len(record.sale_ids) #cuenta general
            record.sale_order_count = self.env['sale.order'].search_count([('exdoo_request_id', '=', record.id)]) #cuenta en especifico (con fltros)
            
    def _compute_purchase_order_count(self):
        for record in self:
            record.purchase_order_count = self.env['purchase.order'].search_count([('exdoo_request_id', '=', record.id)])
    
    def _compute_invoice_count(self):
        for request in self:
            request.invoice_count = self.env['account.move'].search_count([('exdoo_request_id', '=', request.id)])
             
    def action_confirm_request(self, sale_order_id):
        sale_order_lines = []
        purchase_order_lines_by_supplier = defaultdict(list)  # Para agrupar líneas por proveedor

        for record in self.details_id:
            if not record.id_warehouse:
                raise UserError("Debes seleccionar un almacén antes de confirmar.")

            product = record.product_id

            if product:
                available_qty = product.with_context(
                    warehouse=record.id_warehouse.id
                ).qty_available

                if record.quantity > available_qty:
                    auto_purchase = self.company_id.auto_purchase_on_confirm

                    if auto_purchase:
                        missing_qty = record.quantity - available_qty

                        supplier = product.seller_ids[0].partner_id if product.seller_ids else None

                        if not supplier:
                            raise UserError(f"No se encontró un proveedor para el producto: {product.name}")

                        purchase_line_data = {
                            'product_id': product.id,
                            'name': product.name,
                            'product_qty': missing_qty,
                            'product_uom': record.unit_of_measurement.id,
                            'price_unit': record.unit_price,
                            'date_planned': fields.Date.today(),
                            #'picking_type_id': record.id_warehouse.pick_type_id.id,
                        }
                        purchase_order_lines_by_supplier[supplier.id].append(purchase_line_data)
                        
                        

                    sale_order_line_data = {
                        'order_id': sale_order_id,
                        'product_id': product.id,
                        'product_uom_qty': record.quantity,
                        'price_unit': record.unit_price,
                    }
                    sale_order_lines.append(sale_order_line_data)

                else:
                    sale_order_line_data = {
                        'order_id': sale_order_id,
                        'product_id': product.id,
                        'product_uom_qty': record.quantity,
                        'price_unit': record.unit_price,
                    }
                    sale_order_lines.append(sale_order_line_data)

        for supplier_id, purchase_lines in purchase_order_lines_by_supplier.items():
            self.create_purchase(supplier_id, purchase_lines)

        return sale_order_lines

    def create_purchase(self, supplier_id, purchase_lines):
        """Crear una orden de compra con todas las líneas de productos del mismo proveedor."""
        supplier = self.env['res.partner'].browse(supplier_id)

        purchase_order = self.env['purchase.order'].create({
            'partner_id': supplier.id,
            'exdoo_request_id': self.id,
            'picking_type_id': self.warehouse_id.in_type_id.id,
            'order_line': [(0, 0, line) for line in purchase_lines],
        })
    
        purchase_order.button_confirm()
        
        return {
            'name': 'Compra',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'res_id': purchase_order.id,
        }

                                 
    @api.model
    def create(self, variables):
        if self._name == 'exdoo.request':
            sequence_obj = self.env['ir.sequence']
            correlative = sequence_obj.next_by_code('sequence.sale.request')
            variables['name'] = correlative
            return super(ExdooRequest, self).create(variables)

    @api.depends('details_id.rd_subtotal', 'details_id.rd_tax', 'details_id.rd_total')
    def _compute_amounts(self):
        """Compute the total amounts of the SO."""
        for order in self:
            order = order.with_company(order.company_id)
            order_lines = order.details_id.filtered(lambda x: x.product_id) # cuenta las lineas de venta

            if order.company_id.tax_calculation_rounding_method == 'round_globally':
                tax_results = order.env['account.tax']._compute_taxes([
                    line._convert_to_tax_base_line_dict()
                    for line in order_lines
                ])
                totals = tax_results['totals']
                amount_untaxed = totals.get(order.currency_id, {}).get('amount_untaxed', 0.0)
                amount_tax = totals.get(order.currency_id, {}).get('amount_tax', 0.0)
            else:
                amount_untaxed = sum(order_lines.mapped('rd_subtotal'))
                amount_tax = sum(order_lines.mapped('rd_tax'))

            order.base = amount_untaxed
            order.taxes = amount_tax
            order.total = order.base + order.taxes
           
    @api.onchange('customer')
    def _onchange_costumer(self):
        if self.customer:
            self.payment_term = self.customer.property_payment_term_id

class RequestDetails(models.Model):
    _name='request.details'
    _description = "Exdoo Request Details"

    product_id = fields.Many2one(comodel_name="product.product", string="Producto")
    quantity = fields.Float(string="Cantidad", required=True, store=True,  default=1.0)
    unit_of_measurement = fields.Many2one(comodel_name="uom.uom", string="Unidad de Medida")
    
    tax_id = fields.Many2many(
        comodel_name="account.tax", 
        string="Tipo de Impuesto",
        compute="_compute_tax_id",
        store=True, readonly=False, precompute=True,
        domain=[('type_tax_use','=','sale')]
        )

    unit_price = fields.Float(string="Precio Unitario",)

    rd_tax = fields.Monetary(string="Impuesto", compute="_compute_amount", precompute=True)
    rd_subtotal = fields.Monetary(string="Subtotal", compute="_compute_amount", precompute=True)
    rd_total = fields.Monetary(string="Total", compute="_compute_amount", precompute=True)

    currency_id = fields.Many2one(comodel_name = 'res.currency', string = 'Moneda', related="id_request.currency_id")
    id_request = fields.Many2one(comodel_name="exdoo.request", string="ids_request")
    
    discount = fields.Float(string="% Descuento", default=0.0)
    is_admin_user = fields.Boolean(string="Es Administrador", compute="_compute_is_admin_user")
    
    id_warehouse = fields.Many2one(comodel_name="stock.warehouse", string="Almacen", related="id_request.warehouse_id")
    
    @api.depends('product_id', 'id_request.company_id')
    def _compute_tax_id(self):
        taxes_by_product_company = defaultdict(lambda: self.env['account.tax'])
        lines_by_company = defaultdict(lambda: self.env['request.details'])
        cached_taxes = {}
        for line in self:
            lines_by_company[line.id_request.company_id] += line
        for product in self.product_id:
            for tax in product.taxes_id:
                taxes_by_product_company[(product, tax.id_request.company_id)] += tax
        for company, lines in lines_by_company.items():
            for line in lines.with_company(company):
                taxes = taxes_by_product_company[(line.product_id, company)]
                if not line.product_id :
                    # Nothing to map
                    line.tax_id = False
                    continue
                fiscal_position = False #line.id_request.fiscal_position_id
                cache_key = (fiscal_position.id, company.id, tuple(taxes.ids))
                cache_key += line._get_custom_compute_tax_cache_key()
                if cache_key in cached_taxes:
                    result = cached_taxes[cache_key]
                else:
                    result = fiscal_position.map_tax(taxes)
                    cached_taxes[cache_key] = result
                # If company_id is set, always filter taxes by the company
                line.tax_id = result

    def _convert_to_tax_base_line_dict(self):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=self.id_request.customer,
            currency=self.id_request.currency_id,
            product=self.product_id,
            taxes=self.tax_id,
            price_unit=self.unit_price,
            quantity=self.quantity,
            discount=self.discount,
            price_subtotal=self.rd_subtotal,
        )

    @api.depends('quantity', 'discount', 'unit_price', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            tax_results = self.env['account.tax'].with_company(line.id_request.company_id)._compute_taxes(
                [line._convert_to_tax_base_line_dict()]
            )
            totals = list(tax_results['totals'].values())[0]
            amount_untaxed = totals['amount_untaxed']
            amount_tax = totals['amount_tax'] 

            line.update({
                'rd_subtotal': amount_untaxed,
                'rd_tax': amount_tax,
                'rd_total': amount_untaxed + amount_tax,
            })

    @api.depends('product_id', 'unit_price', 'quantity')
    def _compute_discount(self):
        for line in self:

            line = line.with_company(line.company_id)
            pricelist_price = line._get_pricelist_price()
            base_price = line._get_pricelist_price_before_discount()

            if base_price != 0:
                discount = (base_price - pricelist_price) / base_price * 100
                if (discount > 0 and base_price > 0) or (discount < 0 and base_price < 0):
                    line.discount = discount

    @api.onchange('product_id')
    def _onchange_product(self):
        if self.product_id:
            self.unit_price = self.product_id.lst_price
            self.unit_of_measurement = self.product_id.uom_po_id
            self.tax_id = self.product_id.taxes_id           
                
    @api.onchange('product_id')                
    def _compute_is_admin_user(self):
        if self.env.user.has_group('exdoo_request.group_exdoo_request_user'):
            self.is_admin_user = True
        else:
            self.is_admin_user = False
      
  