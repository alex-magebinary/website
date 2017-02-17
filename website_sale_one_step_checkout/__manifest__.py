# -*- coding: utf-8 -*-
# © 2015 bloopark systems (<http://bloopark.de>)
# © 2016 Antiun Ingeniería S.L. - Jairo Llopis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name': 'One Step Checkout',
    'category': 'Website',
    'summary': 'Provide an All-In-One Checkout for your website e-commerce',
    'version': '8.0.1.0.0',
    'author': "bloopark systems GmbH & Co. KG, "
              "Antiun Ingeniería S.L., "
              "Odoo Community Association (OCA)",
    'website': "http://www.bloopark.de",
    'license': 'AGPL-3',
    'depends': [
        'website',
        'website_sale_delivery',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/website_sale_osc.xml',
        'views/res_config.xml',
        'views/website_sale_osc.xml',
    ],
    'installable': True,
    'auto_install': False,
}
