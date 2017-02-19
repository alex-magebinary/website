# -*- coding: utf-8 -*-
# © 2015 bloopark systems (<http://bloopark.de>)
# © 2016 Antiun Ingeniería S.L. - Jairo Llopis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale_delivery.controllers.main import WebsiteSaleDelivery
from odoo.http import request
from odoo.report import report_sxw
from odoo import http, SUPERUSER_ID


class WebsiteSale(WebsiteSale):
    mandatory_billing_fields = ["name", "phone", "email", "street", "city", "country_id", "zip"]
    optional_billing_fields = ["street2", "state_id", "vat", "vat_subjected"]


    @http.route(['/shop/checkout'], type='http', auth='public', website=True, multilang=True)
    def checkout(self, **post):
        """Use one step checkout if enabled. Fall back to normal otherwise."""
        # Use normal checkout if OSC is disabled or there is a redirection

        normal = super(WebsiteSale, self).checkout(**post)

        if not request.website.use_osc:
            print "ABOUT TO RETURN NORMAL WEBSITESALE FUNCTION"
            return normal

        # must have a draft sale order with lines at this point, otherwise reset
        order = request.website.sale_get_order()

        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        values = self.checkout_values(**post)


        # if not normal.qcontext:
        #     values = self.checkout_values(**post)
        # else:
        #     values = normal.qcontext

        partner = request.env['res.users'].sudo().browse(request.uid).partner_id

        # get countries dependent on website settings
        countries_domain = []
        if not request.website.use_all_checkout_countries:
            countries_domain = [('id', 'in', request.website.checkout_country_ids.ids)]

        values['countries'] = request.env['res.country'].search(countries_domain)

        print "######################################"
        #print values['checkout']

        if not post and request.uid != request.website.user_id.id and 'checkout' in values:
            values['checkout'].update({'street': partner.street_name,
                                       'street_number': partner.street_number})
        if not post and request.uid != request.website.user_id.id and 'checkout' not in values:
            values['checkout'] = {'street': partner.street_name,
                                       'street_number': partner.street_number}

        result = self.payment(post=post)
        values.update(result.qcontext)

        # Return unified checkout view
        return request.render(
            'website_sale_one_step_checkout.osc_onestepcheckout', values)

    @http.route(['/shop/checkout/confirm_address/'], type='json', auth='public', website=True,
                multilang=True)
    def confirm_address(self, **post):
        """Address controller."""
        # must have a draft sale order with lines at this point, otherwise redirect to shop
        order = request.website.sale_get_order()
        if not order or order.state != 'draft' or not order.order_line:
            request.session['sale_order_id'] = None
            request.session['sale_transaction_id'] = None
            return request.redirect('/shop')

        # if transaction pending / done: redirect to confirmation
        tx = request.context.get('website_sale_transaction')
        if tx and tx.state != 'draft':
            return request.redirect('/shop/payment/confirmation/%s' % order.id)

        orm_partner = request.env['res.partner']

        info = {}
        values = {
            'countries': request.env['res.country'].sudo().search([]),
            'states': request.env['res.country.state'].search([]),
            'checkout': info,
            'shipping': post.get('shipping_different')
        }
        checkout = values['checkout']
        checkout.update(post)

        # TODO: Remove this once below part is adapted
        if 'sale_last_order_id' not in request.session:
            print "==================================="
            print "NO LAST ORDER; ABOUT TO WRITE sale_last_order_id"
            print "==================================="
            request.session['sale_last_order_id'] = request.website.sale_get_order().id


        # TODO: Adapt this part for address validation
        # # see website_sale.main > address()
        # # IF PUBLIC ORDER
        # if order.partner_id.id == request.website.user_id.sudo().partner_id.id:
        #     mode = ('new', 'billing')
        #     country_code = request.session['geoip'].get('country_code')
        #     if country_code:
        #         def_country_id = request.env['res.country'].search([('code', '=', country_code)], limit=1)
        #     else:
        #         def_country_id = request.website.user_id.sudo().country_id
        # # IF ORDER LINKED TO A PARTNER
        # else:
        #     if partner_id > 0:
        #         if partner_id == order.partner_id.id:
        #             mode = ('edit', 'billing')
        #         else:
        #             shippings = Partner.search([('id', 'child_of', order.partner_id.commercial_partner_id.ids)])
        #             if partner_id in shippings.mapped('id'):
        #                 mode = ('edit', 'shipping')
        #             else:
        #                 return Forbidden()
        #         if mode:
        #             values = Partner.browse(partner_id)
        #     elif partner_id == -1:
        #         mode = ('new', 'shipping')
        #     else:  # no mode - refresh without post?
        #         return request.redirect('/shop/checkout')
        #
        # # TODO: adapt this part
        # values['error'] = self.checkout_form_validate(mode, checkout, checkout)
        # if values['error']:
        #     return {
        #         'success': False,
        #         'errors': values['error']
        #     }
        #
        # company = None
        # if 'company' in checkout:
        #     companies = orm_partner.sudo().search([('name', 'ilike', checkout['company']),
        #                                            ('is_company', '=', True)])
        #     company = (companies and companies[0]) or orm_partner.sudo().create({
        #         'name': checkout['company'],
        #         'is_company': True
        #     })
        #
        # checkout['street_name'] = checkout.get('street')
        # if checkout.get('street_number'):
        #     checkout['street'] = checkout.get('street') + ' ' + checkout.get('street_number')
        #
        # billing_info = dict((k, v) for k, v in checkout.items()
        #                     if 'shipping_' not in k and k != 'company')
        # billing_info['parent_id'] = (company and company.id) or None
        #
        # partner = None
        # if request.uid != request.website.user_id.id:
        #     partner = request.env['res.users'].sudo().browse(request.uid).partner_id
        # elif order.partner_id:
        #     users = request.env['res.users'].sudo().search([
        #         ('active', '=', False), ('partner_id', '=', order.partner_id.id)])
        #     if not users or request.website.user_id.id not in users.ids:
        #         partner = order.partner_id
        #
        # if partner:
        #     partner.sudo().write(billing_info)
        # else:
        #     partner = orm_partner.sudo().create(billing_info)
        #
        # shipping_partner = None
        # if int(checkout.get('shipping_id')) == -1:
        #     shipping_info = {
        #         'phone': post['shipping_phone'],
        #         'zip': post['shipping_zip'],
        #         'street': post['shipping_street'] + ' ' + post.get('shipping_street_number'),
        #         'street_name': post['shipping_street'],
        #         'street_number': post['shipping_street_number'],
        #         'city': post['shipping_city'],
        #         'name': post['shipping_name'],
        #         'email': post['email'],
        #         'type': 'delivery',
        #         'parent_id': partner.id,
        #         'country_id': post['shipping_country_id'],
        #         'state_id': post['shipping_state_id'],
        #     }
        #     domain = [(key, '_id' in key and '=' or 'ilike', '_id' in key and value and int(
        #         value) or value)
        #               for key, value in shipping_info.items() if key in
        #               self.mandatory_billing_fields + ['type', 'parent_id']]
        #     shipping_partners = orm_partner.sudo().search(domain)
        #     if shipping_partners:
        #         shipping_partner = shipping_partners[0]
        #         shipping_partner.write(shipping_info)
        #     else:
        #         shipping_partner = orm_partner.sudo().create(shipping_info)
        #
        # order_info = {
        #     'partner_id': partner.id,
        #     'message_follower_ids': [(4, partner.id), (3, request.website.partner_id.id)],
        #     'partner_invoice_id': partner.id
        # }
        # order_info.update(request.env['sale.order'].sudo().onchange_partner_id(
        #     partner.id)['value'])
        # # we need to update partner_shipping_id after onchange_partner_id() call
        # # otherwise the deselection of the option 'Ship to a different address'
        # # would be overwritten by an existing shipping partner type
        # order_info.update({
        #     'partner_shipping_id': (shipping_partner and shipping_partner.id) or partner.id})
        # order_info.pop('user_id')
        #
        # order.sudo().write(order_info)
        # request.session['sale_last_order_id'] = order.id
        return {'success': True}

    @http.route(['/shop/checkout/change_delivery'], type='json', auth="public", website=True, multilang=True)
    def change_delivery(self, **post):
        """
        If delivery method is was changed in frontend.

        Change and apply delivery carrier / amount to sale order.
        """
        order = request.website.sale_get_order()
        carrier_id = int(post.get('carrier_id'))

        print "Within change_delivery, (order, carrier_id): ", (order, carrier_id)

        return self.do_change_delivery(order, carrier_id)

    def do_change_delivery(self, order, carrier_id):
        """Apply delivery amount to current sale order."""
        if not order or not carrier_id:
            return {'success': False}

        print "Within do_change_delivery, (order, carrier_id)", order, carrier_id

        # order_id is needed to get delivery carrier price
        # TODO: does this what it's supposed to do?
        if not request.context.get('order_id'):
            print ("In if clause")

            context = dict(request.context)
            context.update({'order_id': order.id})

        # recompute delivery costs
        print "Recompute delivery costs"
        request.env['sale.order']._check_carrier_quotation(force_carrier_id=carrier_id)

        print "generate updated total prices"
        # generate updated total prices
        updated_order = request.website.sale_get_order()

        print "***********************"
        print "request.env['product.product']._name"
        print(request.env['product.product']._name)

        rml_obj = report_sxw.rml_parse(request.cr, SUPERUSER_ID,
                                       request.env['product.product']._name,
                                       context=context)
        price_digits = rml_obj.get_digits(dp='Product Price')

        print "get additional tax information"
        # get additional tax information
        # tax_overview = request.env['sale.order'].tax_overview(updated_order)

        result = {
            'success': True,
            'order_total': rml_obj.formatLang(updated_order.amount_total,
                                              digits=price_digits),
            # 'order_subtotal': rml_obj.formatLang(updated_order.amount_subtotal,
            #                                      digits=price_digits),
            'order_total_taxes': rml_obj.formatLang(updated_order.amount_tax,
                                                    digits=price_digits),
            # 'order_total_tax_overview': tax_overview,
            'order_total_delivery': rml_obj.formatLang(
                updated_order.amount_delivery, digits=price_digits)
        }

        print result

        return result

    @http.route(['/page/terms_and_conditions/'], type='http', auth="public",
                website=True, multilang=True)
    def checkout_terms(self, **opt):
        """Function for terms of condition."""
        return request.render('website_sale_one_step_checkout.checkout_terms')




    # def checkout_values(self, **kw):
    #     """Additional information for unified checkout."""
    #     data = kw or dict()
    #     print "OSC CHECKOUT_VALUES: ", data
    #     values = super(WebsiteSale, self).checkout_values(**kw)
    #     if not request.website.use_osc:
    #         return values
    #
    #     # Sale order
    #     values["website_sale_order"] = request.website.sale_get_order()
    #
    #     # Payment info
    #     payment = self.payment()
    #     values.update(payment.qcontext)
    #
    #     # Default payment
    #     try:
    #         # The one the user chose, when being called from confirm_order()
    #         values["default_acquirer_id"] = int(data["acquirer"])
    #     except (KeyError, ValueError):
    #         # Somebody tried to hack us, or it's being called from checkout()
    #         try:
    #             values["default_acquirer_id"] = values["acquirers"][0].id
    #         except (KeyError, IndexError):
    #             # There are no acquirers
    #             pass
    #
    #     # Remove partner to display the "or Sign in" button
    #     del values["partner"]
    #
    #     return values

    # @http.route()
    # def confirm_order(self, **post):
    #     """One step order confirmation if enabled, default otherwise."""
    #     normal = super(WebsiteSale, self).confirm_order(**post)
    #
    #     # Fall back to original logic if OSC is disabled
    #     if not request.website.use_osc:
    #         return normal
    #
    #     print 'OSC CONFIRM ORDER'
    #
    #     # Something failed at confirm
    #     if "errors" in normal.qcontext:
    #         checkout = self.checkout(**post)
    #         checkout.qcontext.update(normal.qcontext)
    #         return checkout
    #
    #     # TODO Peta la llamada JSONRPC a '/shop/payment/transaction/'
    #     raise NotImplementedError


# class WebsiteSaleDelivery(WebsiteSaleDelivery):
#     @http.route(['/shop/payment'], type='http', auth="public", website=True)
#     def payment(self, carrier_id=None, **post):
#         """
#         Fall back to normal if OSC is not enabled.
#
#         Otherwise update Delivery method and Price according to the newly chosen method
#         while staying on the same checkout page.
#         """
#         normal = super(WebsiteSaleDelivery, self).payment(**post)
#         if not request.website.use_osc:
#             return normal
#
#         order = request.website.sale_get_order()
#         carrier_id = carrier_id
#         if carrier_id:
#             carrier_id = int(carrier_id)
#         if order:
#             order._check_carrier_quotation(force_carrier_id=carrier_id)
#             if carrier_id:
#                 return request.redirect("/shop/checkout") #request.redirect("/shop/payment")
#
#         # TODO: take care of this --> add payment method to WebsiteSale above?
#         return normal
#
#     def order_lines_2_google_api(self, order_lines):
#         """ Transforms a list of order lines into a dict for google analytics """
#         order_lines_not_delivery = order_lines.filtered(lambda line: not line.is_delivery)
#         return super(WebsiteSaleDelivery, self).order_lines_2_google_api(order_lines_not_delivery)
#
#     def order_2_return_dict(self, order):
#         """ Returns the tracking_cart dict of the order for Google analytics """
#         ret = super(WebsiteSaleDelivery, self).order_2_return_dict(order)
#         for line in order.order_line:
#             if line.is_delivery:
#                 ret['transaction']['shipping'] = line.price_unit
#         return ret
