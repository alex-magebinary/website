# -*- coding: utf-8 -*-
# © 2017 bloopark systems (<http://bloopark.de>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models, api


class Website(models.Model):
    """Adds the fields for options of the OSC."""
    _inherit = 'website'

    use_osc = fields.Boolean(
        string='Use OSC',
        default=True,)
