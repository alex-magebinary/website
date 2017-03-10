# -*- coding: utf-8 -*-
# © 2017 bloopark systems (<http://bloopark.de>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name': 'One Step Checkout',
    'category': 'Website',
    'summary': 'Provide an All-In-One Checkout for your website e-commerce',
    'version': '1.0',
    'author': "bloopark systems GmbH & Co. KG",
    'website': "http://www.bloopark.de",
    'license': 'AGPL-3',
    'depends': [
        'website',
        'website_sale'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config.xml',
        'views/website_sale_one_step_checkout.xml',
    ],
    'installable': True,
    'auto_install': False,
}
