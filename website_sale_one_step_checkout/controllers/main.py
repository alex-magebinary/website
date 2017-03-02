# -*- coding: utf-8 -*-
# © 2015 bloopark systems (<http://bloopark.de>)
# © 2016 Antiun Ingeniería S.L. - Jairo Llopis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request, redirect_with_hash
from odoo.report import report_sxw
from odoo import http, SUPERUSER_ID
from werkzeug.exceptions import Forbidden


class WebsiteSale(WebsiteSale):
    mandatory_billing_fields = ["name", "phone", "email", "street", "city", "country_id", "zip"]
    optional_billing_fields = ["street2", "state_id", "vat", "vat_subjected"]


    @http.route(['/shop/checkout'], type='http', auth='public', website=True, multilang=True)
    def checkout(self, **post):
        """Use one step checkout if enabled. Fall back to normal otherwise."""
        # if onestepcheckout is deactivated use the normal checkout
        if not request.website.use_osc:
            return super(WebsiteSale, self).checkout(**post)

        # must have a draft sale order with lines at this point, otherwise reset
        order = request.website.sale_get_order()

        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        values = self.checkout_values(**post)

        partner = request.env['res.users'].sudo().browse(request.uid).partner_id

        # get countries dependent on website settings
        countries_domain = []
        if not request.website.use_all_checkout_countries:
            countries_domain = [('id', 'in', request.website.checkout_country_ids.ids)]

        values['countries'] = request.env['res.country'].search(countries_domain)

        # To avoid access problems when rendering
        # the address template for public user
        if post.get('public_user'):
            return values

        result = self.payment(post=post)
        values.update(result.qcontext)

        # Avoid useless rendering if called in ajax
        if post.get('xhr'):
            return 'ok'

        return request.render(
            'website_sale_one_step_checkout.osc_onestepcheckout', values)


    @http.route(['/shop/checkout/validate_address_form'], type='json', auth='public', website=True, multilang=True)
    def validate_address_form(self):
        order = request.website.sale_get_order()

        if not order:
            return {
                'success': False
            }

        if order.partner_id.id != request.website.user_id.sudo().partner_id.id:
            for f in self._get_mandatory_billing_fields():
                if not order.partner_id[f]:
                    return {
                        'success':False,
                        'partner_id':order.partner_id.id
                    }

            return {
                'success':True
                }

        elif order.partner_id.id == request.website.user_id.sudo().partner_id.id:
            return {
                'success': False
            }


    # TODO CHANGE NAME AND URL?
    @http.route(['/shop/checkout/render_address'], type='json', auth='public', website=True, multilang=True)
    def renderAddress(self, **kw):
        Partner = request.env['res.partner'].with_context(show_address=1).sudo()
        order = request.website.sale_get_order(force_create=1)
        def_country_id = order.partner_id.country_id
        values, errors = {}, {}

        mode = (False,False)
        partner_id = int(kw.get('partner_id', -1))
        shippings = []

        # IF PUBLIC ORDER
        if order.partner_id.id == request.website.user_id.sudo().partner_id.id:

            mode = ('new', 'billing')

            print("# IF PUBLIC ORDER")
            print order.partner_id.id
            country_code = request.session['geoip'].get('country_code')
            if country_code:
                def_country_id = request.env['res.country'].search([('code', '=', country_code)], limit=1)
            else:
                def_country_id = request.website.user_id.sudo().country_id
        # IF ORDER LINKED TO A PARTNER
        else:
            print "# IF ORDER LINKED TO A PARTNER"
            if partner_id > 0:
                print "if partner_id > 0:"
                if partner_id == order.partner_id.id:
                    mode = ('edit', 'billing')
                else:
                    shippings = Partner.search([('id', 'child_of', order.partner_id.commercial_partner_id.ids)],
                                               order='id desc')
                    if partner_id in shippings.mapped('id'):
                        mode = ('edit', 'shipping')
                    else:
                        return Forbidden()
                print "MODE", mode
                if mode:
                    # for fetching pre-filled form values
                    values = Partner.browse(partner_id)
            elif partner_id == -1:
                print "elif partner_id == -1:"
                mode = ('new', 'shipping')
            else:  # no mode - refresh without post?
                return request.redirect('/shop/checkout')


        # IF POSTED
        if 'submitted' in kw:
            print "submitted"
            pre_values = self.values_preprocess(order, mode, kw)
            errors, error_msg = self.checkout_form_validate(mode, kw, pre_values)
            post, errors, error_msg = self.values_postprocess(order, mode, pre_values, errors, error_msg)

            if errors:
                errors['error_message'] = error_msg
                # [REF]
                # HIGHLIGHT WRONG INPUT
                return {
                    'success': False,
                    'errors': errors
                }
            else:
                partner_id = self._checkout_form_save(mode, post, kw)
                print "order.partner_id ", order.partner_id
                print "partner_id ", partner_id
                if mode[1] == 'billing':
                    order.partner_id = partner_id
                    order.onchange_partner_id()
                elif mode[1] == 'shipping':
                    order.partner_shipping_id = partner_id

                order.message_partner_ids = [(4, partner_id), (3, request.website.partner_id.id)]

                if not shippings:
                    shippings = Partner.search([('id', 'child_of', order.partner_id.commercial_partner_id.ids)],
                                               order='id desc')

                # [REF]
                render_values = {
                    'shippings':shippings,
                    'order':order
                }

                if mode[0] == 'new':
                    # New public user address
                    # To avoid access problems when rendering
                    # the address template, fetch new values
                    render_values = self.checkout(**{'public_user': True})

                template = request.env['ir.ui.view'].render_template("website_sale_one_step_checkout.address",
                                                                     render_values)

                return {
                    'success':True,
                    'template':template,
                    'mode':mode
                }


        country = 'country_id' in values and values['country_id'] != '' and request.env['res.country'].browse(
            int(values['country_id']))
        country = country and country.exists() or def_country_id
        render_values = {
            'partner_id': partner_id,
            'mode': mode,
            'checkout': values,
            'country': country,
            'countries': country.get_website_sale_countries(mode=mode[1]),
            "states": country.get_website_sale_states(mode=mode[1]),
            'error': errors,
            'callback': kw.get('callback'),
        }

        template = request.env['ir.ui.view'].render_template("website_sale_one_step_checkout.checkout_new_address_modal", render_values)
        return {
            'success': True,
            'template': template,
            'type': mode[1]
        }


    @http.route(['/shop/checkout/validate_checkout/'], type='json', auth='public', website=True,
                multilang=True)
    def validate_checkout(self, **post):
        """Address controller."""
        print 'validate_checkout'
        # must have a draft sale order with lines at this point, otherwise redirect to shop
        SaleOrder = request.env['sale.order']
        order = request.website.sale_get_order()

        if not order or order.state != 'draft' or not order.order_line:
            request.session['sale_order_id'] = None
            request.session['sale_transaction_id'] = None
            return request.redirect('/shop')

        # [REF] shop/confirm_order
        order.onchange_partner_shipping_id()
        order.order_line._compute_tax_id()
        if not request.session.get('sale_last_order_id'):
            print 'no sale last order, setting it'
            request.session['sale_last_order_id'] = order.id
        extra_step = request.env.ref('website_sale.extra_info_option')
        # TODO: HOW TO HANDLE THIS CASE?
        if extra_step.active:
            # TODO CONTROLLER /shop/extra_info NEEDS TO BE REWRITTEN?
            return request.redirect("/shop/extra_info")

        # if transaction pending / done: redirect to confirmation
        tx = request.env.context.get('website_sale_transaction')
        if tx and tx.state != 'draft':
            return request.redirect('/shop/payment/confirmation/%s' % order.id)

        # [REF] /shop/payment
        shipping_partner_id = False
        if order:
            if order.partner_shipping_id:
                shipping_partner_id = order.partner_shipping_id.id
            else:
                shipping_partner_id = order.partner_invoice_id.id

        # [REF] /shop/payment
        # TODO: ADAPT BELOW PART FROM THE ORIGINAL CONTROLLER
        values = {
            'website_sale_order': order
        }
        values['errors'] = SaleOrder._get_errors(order)
        values.update(SaleOrder._get_website_data(order))

        # TODO TAKE CARE OF ERRORS


    @http.route(['/shop/checkout/change_delivery'], type='json', auth="public", website=True, multilang=True)
    def change_delivery(self, **post):
        """
        If delivery method was changed in frontend.

        Change and apply delivery carrier / amount to sale order.
        """
        order = request.website.sale_get_order()
        carrier_id = int(post.get('carrier_id'))

        return self.do_change_delivery(order, carrier_id)

    def do_change_delivery(self, order, carrier_id):
        """Apply delivery amount to current sale order."""
        if not order or not carrier_id:
            return {'success': False}

        # order_id is needed to get delivery carrier price
        # TODO: recheck if this is correct
        if not request.context.get('order_id'):
            context = dict(request.context)
            context.update({'order_id': order.id})

        # generate updated total prices
        updated_order = request.website.sale_get_order()
        updated_order._check_carrier_quotation(force_carrier_id=carrier_id)
        updated_order.delivery_set()

        rml_obj = report_sxw.rml_parse(request.cr, SUPERUSER_ID,
                                       request.env['product.product']._name,
                                       context=context)
        price_digits = rml_obj.get_digits(dp='Product Price')

        result = {
            'success': True,
            'order_total': rml_obj.formatLang(updated_order.amount_total,
                                              digits=price_digits),
            'order_total_taxes': rml_obj.formatLang(updated_order.amount_tax,
                                                    digits=price_digits),
            'order_total_delivery': rml_obj.formatLang(
                updated_order.amount_delivery, digits=price_digits)
        }

        return result

    # TODO: is this part necessary?
    @http.route()
    def cart(self, **post):
        """If only one active delivery carrier exists apply this delivery to sale order."""
        response_object = super(WebsiteSale, self).cart(**post)
        values = response_object.qcontext
        dc_ids = request.env['delivery.carrier'].sudo().search(
            [('active', '=', True), ('website_published', '=', True)])
        change_delivery = True
        if dc_ids and len(dc_ids) == 1:
            for line in values['website_sale_order'].order_line:
                if line.is_delivery:
                    change_delivery = False
                    break
            if change_delivery:
                self.do_change_delivery(values['website_sale_order'], dc_ids[0])

        return request.render(response_object.template, values)


    @http.route(['/page/terms_and_conditions/'], type='http', auth="public",
                website=True, multilang=True)
    def checkout_terms(self, **opt):
        """Function for terms of condition."""
        return request.render('website_sale_one_step_checkout.checkout_terms')
