# -*- coding: utf-8 -*-
# © 2015 bloopark systems (<http://bloopark.de>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models, api


class Website(models.Model):
    """Adds the fields for options of the OSC."""
    _inherit = 'website'

    use_osc = fields.Boolean(
        string='Use OSC',
        default=True,)
    use_all_checkout_countries = fields.Boolean(
        string='Use All Countries in Checkout',
        default=True, )
    checkout_country_ids = fields.Many2many(
        'res.country',
        'checkout_country_rel',
        'website_id', 'country_id',
        'Checkout Countries')
