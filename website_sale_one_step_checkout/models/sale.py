# -*- coding: utf-8 -*-
##############################################################################
#
# Odoo, an open source suite of business apps
# This module copyright (C) 2015 bloopark systems (<http://bloopark.de>).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import api, fields, models
from odoo.addons import decimal_precision

# TODO check if needed
class SaleOrder(models.Model):

    """Overwrites and add Definitions to module: sale."""

    _inherit = 'sale.order'

    amount_subtotal = fields.Float(
        compute='_compute_amount_subtotal',
        digits=decimal_precision.get_precision('Account'),
        string='Subtotal Amount',
        store=True,
        help="The amount without anything.",
        track_visibility='always'
    )

    @api.depends('order_line', 'order_line.price_subtotal')
    def _compute_amount_subtotal(self):
        """compute Function for amount_subtotal."""
        for rec in self:
            line_amount = sum([line.price_subtotal for line in
                               rec.order_line if not line.is_delivery])
            currency = rec.pricelist_id.currency_id
            rec.amount_subtotal = currency.round(line_amount)



# TODO remove
# class ResPartner(models.Model):
#
#     """Add Fields to res.partner."""
#
#     _inherit = 'res.partner'
#
#     street_name = fields.Char(string='Street name')
#     street_number = fields.Char(tring='Street number')
