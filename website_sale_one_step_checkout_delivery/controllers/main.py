# -*- coding: utf-8 -*-
from odoo.addons.website_sale_one_step_checkout.controllers.main import WebsiteSale
from odoo import http, SUPERUSER_ID
from odoo.http import request


class WebsiteSaleOneStepCheckoutDelivery(WebsiteSale):
    @http.route(['/shop/checkout/change_delivery'], type='json', auth="public", website=True, multilang=True)
    def change_delivery(self, **post):
        """
        If delivery method was changed in frontend.

        Change and apply delivery carrier / amount to sale order.
        """
        print "change_delivery"
        order = request.website.sale_get_order()
        carrier_id = int(post.get('carrier_id'))

        return self.do_change_delivery(order, carrier_id)

    def do_change_delivery(self, order, carrier_id):
        """Apply delivery amount to current sale order."""
        print "do_change_delivery"
        if not order or not carrier_id:
            return {'success': False}

        # order_id is needed to get delivery carrier price
        if not request.context.get('order_id'):
            context = dict(request.context)
            context.update({'order_id': order.id})

        # generate updated total prices
        updated_order = request.website.sale_get_order()
        updated_order._check_carrier_quotation(force_carrier_id=carrier_id)
        updated_order.delivery_set()

        result = {
            'success': True,
            'order_total': updated_order.amount_total,
            'order_total_taxes': updated_order.amount_tax,
            'order_total_delivery': updated_order.amount_delivery
        }

        return result

# # TODO ??
# class WebsiteSale(WebsiteSale):
#     @http.route()
#     def cart(self, **post):
#         """If only one active delivery carrier exists apply this delivery to sale order."""
#         response_object = super(WebsiteSale, self).cart(**post)
#         values = response_object.qcontext
#         dc_ids = request.env['delivery.carrier'].sudo().search(
#             [('active', '=', True), ('website_published', '=', True)])
#         change_delivery = True
#         if dc_ids and len(dc_ids) == 1:
#             for line in values['website_sale_order'].order_line:
#                 if line.is_delivery:
#                     change_delivery = False
#                     break
#             if change_delivery:
#                 WebsiteSaleOneStepCheckoutDelivery.do_change_delivery(values['website_sale_order'], dc_ids[0])
#
#         return request.render(response_object.template, values)