# -*- coding: utf-8 -*-
# © 2017 bloopark systems (<http://bloopark.de>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name': "One Step Checkout Delivery",
    'category': 'Website',

    'summary': """Add Delivery Costs to One-Step-Checkout""",

    'description': """
Delivery Costs
==============
""",
    'author': "bloopark systems GmbH & Co. KG",
    'website': "http://www.bloopark.de",
    'license': 'AGPL-3',
    'version': '1.0',
    'depends': [
        'website_sale_delivery',
        'website_sale_one_step_checkout'],
    'data': [
        'views/templates.xml',
    ],
    'installable': True,
    'auto_install': False,
}