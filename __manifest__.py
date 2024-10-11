# -*- coding:utf-8 -*-

{
    'name': 'exdoo_request',
    'version': '1.0',
    'depends': [
      'base',
      'account', 
      'contacts',
      'sale'
      ],
    'author': 'Gilberto C. O.',
    'category': 'Sale',
    'website': 'http://www.google.com',
    "license" : "AGPL-3",
    'description': '''
      
      Este modulo servira como un control de ventas, compras y almacen

    ''',    
    'data': [
      'security/req_groups.xml',
      'security/ir.model.access.csv',
      'data/sequence.xml',
      'views/request_view.xml',
      'views/ppt_termns.xml',
      'views/ers_settings.xml',
      'views/menu.xml'
    ],
}