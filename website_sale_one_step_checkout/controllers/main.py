# -*- coding: utf-8 -*-
# © 2015 bloopark systems (<http://bloopark.de>)
# © 2016 Antiun Ingeniería S.L. - Jairo Llopis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale_delivery.controllers.main import WebsiteSaleDelivery
from odoo.http import request, redirect_with_hash
from odoo.report import report_sxw
from odoo import http, SUPERUSER_ID


class WebsiteSale(WebsiteSale):
    mandatory_billing_fields = ["name", "phone", "email", "street", "city", "country_id", "zip"]
    optional_billing_fields = ["street2", "state_id", "vat", "vat_subjected"]


    @http.route(['/shop/checkout'], type='http', auth='public', website=True, multilang=True)
    def checkout(self, **post):
        """Use one step checkout if enabled. Fall back to normal otherwise."""
        # Use normal checkout if OSC is disabled or there is a redirection
        if not request.website.use_osc:
            return super(WebsiteSale, self).checkout(**post)

        # must have a draft sale order with lines at this point, otherwise reset
        order = request.website.sale_get_order()

        # TODO: remove?
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

    def checkout_values(self, **kw):
        values = super(WebsiteSale, self).checkout_values(**kw)
        order = values.get('order', False)
        billings = []
        if order and order.partner_id != request.website.user_id.sudo().partner_id:
            Partner = order.partner_id.with_context(show_address=1).sudo()
            billings = Partner.search([
                ("id", "child_of", order.partner_id.commercial_partner_id.ids),
                ("type", "=", "invoice")
            ], order='id desc')
            billings = billings
            if billings:
                if kw.get('partner_id'):
                    partner_id = int(kw.get('partner_id'))
                    if partner_id in billings.mapped('id'):
                        order.partner_billing_id = partner_id

        values['billings'] = billings
        return values

    # TODO CHANGE NAME AND URL?
    @http.route(['/shop/checkout/render_address'], type='json', auth='public', website=True, multilang=True)
    def renderAddress(self, **kw):
        Partner = request.env['res.partner'].with_context(show_address=1).sudo()
        order = request.website.sale_get_order(force_create=1)
        # TODO use other default values ,maybe 'new', 'billing'
        mode = (False, False)
        def_country_id = order.partner_id.country_id
        values, errors = {}, {}

        partner_id = int(kw.get('partner_id', -1))
        parent_id = order.partner_id.id

        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        # IF PUBLIC ORDER
        if order.partner_id.id == request.website.user_id.sudo().partner_id.id:
            parent_id = False
            mode = ('new', 'billing')
            country_code = request.session['geoip'].get('country_code')
            if country_code:
                def_country_id = request.env['res.country'].search([('code', '=', country_code)], limit=1)
            else:
                def_country_id = request.website.user_id.sudo().country_id
        # IF ORDER LINKED TO A PARTNER
        else:
            print "ORDER LINKED TO A PARTNER"
            # [REF]
            # CASE WHERE PARTNER WANTS TO ADD A NEW BILLING ADDRESS
            # SET mode
            if 'mode' in kw:
                mode = tuple(kw['mode'])
            if partner_id > 0:
                if partner_id == order.partner_invoice_id.id:
                    mode = ('edit', 'billing')
                else:
                    # [REF]
                    shippings = Partner.search([('type','=', 'delivery'), ('parent_id','=',parent_id)])
                    if partner_id in shippings.mapped('id'):
                        mode = ('edit', 'shipping')
                    else:
                        return Forbidden()
                # [REF]
                # Seems like values is never used again
                # TODO FIX THIS
                # if mode:
                #     values = Partner.browse(partner_id)
                #     print "****************************"
                #     print "****************************"
                #     print "values: %s, mode: %s" % (values, mode)
                #     print "****************************"
                #     print "****************************"

            elif partner_id == -1 and 'mode' not in kw:
                mode = ('new', 'shipping')

        # IF POSTED
        if 'submitted' in kw:
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
                # [REF]
                if not parent_id:
                    parent_id = self._create_partner(post)
                if mode[0]=='new':
                    post['parent_id'] = parent_id
                    if mode[1] == 'billing':
                        post['type'] = 'invoice'
                    elif mode[1] == 'shipping':
                        post['type'] = 'delivery'

                partner_id = self._checkout_form_save(mode, post, kw)

                if mode[1] == 'billing':
                    # [REF]
                    order.partner_invoice_id = partner_id
                elif mode[1] == 'shipping':
                    order.partner_shipping_id = partner_id
                    order.onchange_partner_shipping_id()

                # TODO SAVE TO REMOVE THIS PART NOW?
                # [REF]
                # Needed for rendering the address template
                # Must be the according partner_id as res.partner object
                #partner_id_correct_type = type(partner_id) is not type(values) and type(partner_id) is not int
                contact = partner_id #if partner_id_correct_type else values

                order.message_partner_ids = [(4, partner_id), (3, request.website.partner_id.id)]
                if not errors:
                    # [REF]
                    render_values = {
                        'contact': contact,
                        'selected': 1,
                        'readonly': 1
                    }
                    template = request.env['ir.ui.view'].render_template("website_sale.address_kanban", render_values)
                    return {
                        'success': True,
                        'template': template,
                        'type': mode[1]
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
        print(render_values)
        return {
            'success': True,
            'template': template,
            'type': mode[1]
        }

    def _create_partner(self, values):
        '''
        GET ADDRESS DATA AND SAVE THEM INTO A DICT
        CREATE PARTNER
        RETURN partner_id which will be used as parent_id and address data
        :param values:  dict consisting of address values
        :return:        partner_id
        '''
        for key, val in values.items():
            if key in self._get_address_fields():
                del values[key]
        return request.env['res.partner'].sudo().create(values)

    def _get_address_fields(self):
        return ['city', 'street', 'street2', 'zip', 'state_id', 'country_id']


    # TODO REMOVE
    @http.route(['/shop/checkout/validate_address'], type='json', auth='public', website=True, multilang=True)
    def validate_address(self, **kw):
        Partner = request.env['res.partner'].with_context(show_address=1).sudo()
        order = request.website.sale_get_order()

        # Needed for ?
        partner_id = int(kw.get('partner_id', -1))

        # mode: tuple ('new|edit', 'billing|shipping')
        mode = (kw['address_mode_type'], kw['address_mode_name'])

        # TODO: For edit button: Make sure how to translate the
        # below if clauses. We probably don't need some of them,
        # since we pass mode directly from JS


        print "#################"
        print kw
        print "#################"


        # IF PUBLIC ORDER
        if order.partner_id.id == request.website.user_id.sudo().partner_id.id:
            print "PUBLIC ORDER"
            country_code = request.session['geoip'].get('country_code')
            if country_code:
                print "COUNTRY CODE"
                def_country_id = request.env['res.country'].search([('code', '=', country_code)], limit=1)
            else:
                print "NO COUNTRY CODE"
                def_country_id = request.website.user_id.sudo().country_id
        # IF ORDER LINKED TO A PARTNER
        else:
            print "ORDER LINKED TO A PARTNER"
            #if partner_id > 0:

                # TODO: dont need this since we pass mode directly
                # if partner_id == order.partner_id.id:
                #     mode = ('edit', 'billing')
                #     print "EDIT BILLING"
                # else:

            if mode[1] == 'shipping':
                shippings = Partner.search([('id', 'child_of', order.partner_id.commercial_partner_id.ids)])
                #     if partner_id in shippings.mapped('id'):
                #         print "EDIT SHIPPING"
                #         mode = ('edit', 'shipping')
                #     else:
                # TODO: why is this forbidden?
                #         return Forbidden()
                if mode[0] == 'edit':
                    # TODO: this partner_id is suppsoed to be the shipping id if mode = ('edit', 'shipping')
                    # TODO: if mode = ('edit', 'billing') its equal to order.partner_id
                    # TODO: WARNING: This effect has to be probably overwritten, since with more billing addresses,
                    # TODO: it won't default to order.partner_id anymore, but the according partner_id has somehow
                    # TODO: to be retrieved when clikcing on the 'Edit' button of the according billing address
                    #
                    # Recheck without OSC to see what I mean
                    values = Partner.browse(partner_id)
            # TODO: dont need this since we pass mode directly
            # elif partner_id == -1:
            #     print "NEW SHIPPING"
            #     mode = ('new', 'shipping')
            #else:  # no mode - refresh without post?
            #    return request.redirect('/shop/checkout')


        print "*************************"
        print "*************************"
        print "*************************"
        print mode
        print "*************************"
        print "*************************"
        print "*************************"

        # POSTED at this point
        pre_values = self.values_preprocess(order, mode, kw)
        errors, error_msg = self.checkout_form_validate(mode, kw, pre_values)
        post, errors, error_msg = self.values_postprocess(order, mode, pre_values, errors, error_msg)

        if errors:
            errors['error_message'] = error_msg
            return {
                'success':False,
                'errors':errors
            }

        # TODO: when new address created either order.partner_id or
        # TODO: order.partner_shipping_id will be overwritten by newly created partner_id.
        # TODO: In odoo core code, partner_id will be passed for rendering. That's not what we're
        # TODO: Doing down there?
        # Added partner_id at beginning of function. Will be retrieved from form element (Edit sibling) and sent via JS

        else:
            partner_id = self._checkout_form_save(mode, post, kw)

            if mode[1] == 'billing':
                order.partner_id = partner_id
                order.onchange_partner_id()
            elif mode[1] == 'shipping':
                order.partner_shipping_id = partner_id

            order.message_partner_ids = [(4, partner_id), (3, request.website.partner_id.id)]
            if not errors:
                partner = request.env['res.partner'].sudo().browse(partner_id.id) # TODO changed this from browse(order.partner_id.id)
                print '................................'
                print '................................'
                print '................................'
                print '................................'
                print '................................'
                print '................................'
                print '................................'
                print '................................'
                print partner
                print '................................'
                print '................................'
                print '................................'
                print '................................'
                print '................................'
                print '................................'
                print '................................'
                print '................................'
                values = {
                    'contact': partner,
                    'selected': 1,
                    'readonly': 1
                }
                template = request.env['ir.ui.view'].render_template("website_sale.address_kanban", values)
                return {
                    'success': True,
                    'template': template,
                    'type': mode[1]
                }

    # TODO REMOVE
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
            request.session['sale_last_order_id'] = request.website.sale_get_order().id


        # TODO: Adapt this part for address validation
        # see website_sale.main > address()
        # IF PUBLIC ORDER
        def_country_id = order.partner_id.country_id
        if order.partner_id.id == request.website.user_id.sudo().partner_id.id:
            mode = ('new', 'billing')
            country_code = request.session['geoip'].get('country_code')
            if country_code:
                def_country_id = request.env['res.country'].search([('code', '=', country_code)], limit=1)
            else:
                def_country_id = request.website.user_id.sudo().country_id
        # IF ORDER LINKED TO A PARTNER
        else:
            if partner_id > 0:
                if partner_id == order.partner_id.id:
                    mode = ('edit', 'billing')
                else:
                    shippings = Partner.search([('id', 'child_of', order.partner_id.commercial_partner_id.ids)])
                    if partner_id in shippings.mapped('id'):
                        mode = ('edit', 'shipping')
                    else:
                        return Forbidden()
                if mode:
                    values = Partner.browse(partner_id)
            elif partner_id == -1:
                mode = ('new', 'shipping')
            else:  # no mode - refresh without post?
                return request.redirect('/shop/checkout')


        # TODO: adapt this part
        values['error'] = self.checkout_form_validate(mode, checkout, checkout)
        if values['error']:

            return {
                'success': False,
                'errors': values['error']
            }
        return {'success': True}

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


    # @http.route('/shop/new_address', type='json', auth='public', website=True, multilang=True)
    # def new_address(self, **kw):
    #     #if not request.website.use_osc:
    #     return super(WebsiteSale, self).address(**kw)
    #     #return request.render('website_sale_one_step_checkout.new_address')

    @http.route(['/page/terms_and_conditions/'], type='http', auth="public",
                website=True, multilang=True)
    def checkout_terms(self, **opt):
        """Function for terms of condition."""
        return request.render('website_sale_one_step_checkout.checkout_terms')
