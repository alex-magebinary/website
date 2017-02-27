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

        
        

        # Avoid useless rendering if called in ajax
        if post.get('xhr'):
            
            
            
            return 'ok'

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
                '|', ("type", "=", "invoice"), ('id', '=', Partner.id)
            ], order='id desc')
            
            
            if billings:
                if kw.get('partner_id'):
                    partner_id = int(kw.get('partner_id'))
                    if partner_id in billings.mapped('id'):
                        order.partner_invoice_id = partner_id
                        # Update partner address data newly selected billing address
                        invoice_vals = order.partner_invoice_id.read(self._get_address_fields())[0]
                        if 'id' in invoice_vals:
                            del invoice_vals['id']
                        if invoice_vals.get('country_id'):
                            invoice_vals['country_id'] = invoice_vals['country_id'][0]
                        if invoice_vals.get('state_id'):
                            invoice_vals['state_id'] = invoice_vals['state_id'][0]
                        
                        
                        order.partner_id.write(invoice_vals)

        values['billings'] = billings
        return values

    # TODO CHANGE NAME AND URL?
    @http.route(['/shop/checkout/render_address'], type='json', auth='public', website=True, multilang=True)
    def renderAddress(self, **kw):
        
        
        Partner = request.env['res.partner'].with_context(show_address=1).sudo()
        order = request.website.sale_get_order(force_create=1)
        def_country_id = order.partner_id.country_id
        prefilled_form_values, errors = {}, {}

        mode = tuple(kw.get('mode', ('new', 'billing')))
        partner_id = int(kw.get('partner_id', -1))
        parent_id = order.partner_id.id

        # IF PUBLIC ORDER
        if order.partner_id.id == request.website.user_id.sudo().partner_id.id:
            parent_id = False
            country_code = request.session['geoip'].get('country_code')
            if country_code:
                def_country_id = request.env['res.country'].search([('code', '=', country_code)], limit=1)
            else:
                def_country_id = request.website.user_id.sudo().country_id
        # IF ORDER LINKED TO A PARTNER
        else:
            
            
            if partner_id > 0:
                # [REF]
                # IN CASE OF EDITING MAKE SURE ACCESS RIGHTS ARE GIVEN
                if mode[0] == 'edit':
                    if mode[1] == 'billing':
                        
                        
                        billings = Partner.search([
                            ("id", "child_of", order.partner_id.commercial_partner_id.ids)
                            , '|', ('type','=', 'invoice'), ("id", "=", order.partner_id.commercial_partner_id.id)]
                                                  , order='id desc')
                        
                        if partner_id not in billings.mapped('id'):
                            return Forbidden()

                    elif mode[1] == 'shipping':
                        # TODO
                        # By default Odoo displays the 'Main' or Default address of the partner as shipping
                        # but it's not saved as type 'delivery', so wont be editable with just the following:
                        # shippings = Partner.search([('type','=', 'delivery'), ('parent_id','=',parent_id)])
                        # shippings = Partner.search([('type', '=', 'delivery'), ('parent_id', '=', parent_id),
                        #                             ("id", "=", partner_id)])

                        shippings = Partner.search([
                            ("id", "child_of", order.partner_id.commercial_partner_id.ids),
                            '|', ("type", "=", "delivery"), ("id", "=", order.partner_id.commercial_partner_id.id)
                        ], order='id desc')

                            # THIS ONE DOESN'T WORK FOR THE MAIN ADDRESS, WILL RETURN FORBIDDEN UPON EDIT
                            # Partner.search([('id', 'child_of', order.partner_id.commercial_partner_id.ids),
                            #                         ('id', '=', partner_id),('type', '=', 'delivery')])
                        

                        if partner_id not in shippings.mapped('id'):
                            return Forbidden()

                    # Fetch pre-filled form values of the address being edited
                    prefilled_form_values = Partner.browse(partner_id)

            #elif partner_id == -1 and mode[1] != 'billing':
             #   mode = ('new', 'shipping')

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
                    
                    parent_id = self._create_partner(post).id
                    
                if mode[0]=='new':
                    
                    
                    post['parent_id'] = parent_id
                    if mode[1] == 'billing':
                        post['type'] = 'invoice'
                    elif mode[1] == 'shipping':
                        post['type'] = 'delivery'
                elif mode[0] == 'edit' and mode[1] == 'billing':
                    post['type'] = 'invoice'

                partner_id = self._checkout_form_save(mode, post, kw)

                if mode[1] == 'billing':
                    # [REF]
                    order.partner_invoice_id = partner_id
                elif mode[1] == 'shipping':
                    order.partner_shipping_id = partner_id
                    # TODO: DOUBLE CHECK THIS
                    
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
                    # Update displayed shipping addresses
                    if mode[1] == 'shipping':
                        
                        # TODO FIGURE OUT WHICH WAY TO GET SHIPPINGS
                        shippings = Partner.search([
                            ("id", "child_of", order.partner_id.commercial_partner_id.ids),
                            '|', ("type", "=", "delivery"), ("id", "=", order.partner_id.commercial_partner_id.id)
                        ], order='id desc')
                        
                        render_values = {
                            'shippings':shippings,
                            'order':order
                        }
                        template = request.env['ir.ui.view'].render_template("website_sale_one_step_checkout.update_displayed_shippings",
                                                                             render_values)
                        return {
                            'success':True,
                            'template':template,
                            'mode':mode
                        }

                    # [REF]
                    # Update displayed billing addresses
                    if mode[1] == 'billing':
                        
                        # billings = Partner.search([('type', '=', 'invoice'), ('parent_id', '=', parent_id)])
                        billings = Partner.search([
                            ("id", "child_of", order.partner_id.commercial_partner_id.ids),
                            ("type", "=", "invoice")], order='id desc')
                        
                        render_values = {
                            'billings':billings,
                            'order':order
                        }
                        template = request.env['ir.ui.view'].render_template("website_sale_one_step_checkout.update_displayed_billings",
                                                                             render_values)
                        return {
                            'success':True,
                            'template':template,
                            'mode':mode
                        }

                    


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
                        'mode': mode
                    }

        country = 'country_id' in prefilled_form_values and prefilled_form_values['country_id'] != '' and request.env['res.country'].browse(
            int(prefilled_form_values['country_id']))
        country = country and country.exists() or def_country_id
        
        render_values = {
            'partner_id': partner_id,
            'mode': mode,
            'checkout': prefilled_form_values,
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


    # TODO UPDATE
    # AT THIS POINT THERE EITHER IS A ALREADY VALIDATE BILLING
    # AND SHIPPING ADDRESS OR NOT.
    # IN CASE ONE OF EITHER OF THOSE IS MISSING,
    # RETURN FALSE, ELSE TRUE
    @http.route(['/shop/checkout/validate_checkout/'], type='json', auth='public', website=True,
                multilang=True)
    def validate_checkout(self, **post):
        """Address controller."""
        # must have a draft sale order with lines at this point, otherwise redirect to shop
        
        order = request.website.sale_get_order()


        # TODO Taken over from v8.0 OSC. Is this necessary?
        if not order or order.state != 'draft' or not order.order_line:
            request.session['sale_order_id'] = None
            request.session['sale_transaction_id'] = None
            return request.redirect('/shop')

        # if transaction pending / done: redirect to confirmation
        tx = request.env.context.get('website_sale_transaction')
        if tx and tx.state != 'draft':
            
            return request.redirect('/shop/payment/confirmation/%s' % order.id)

        # [REF] shop/confirm_order
        order.onchange_partner_shipping_id()
        order.order_line._compute_tax_id()
        
        request.session['sale_last_order_id'] = order.id
        request.website.sale_get_order(update_pricelist=True)
        extra_step = request.env.ref('website_sale.extra_info_option')
        # TODO: HOW TO HANDLE THIS CASE?
        if extra_step.active:
            # TODO CONTROLLER /shop/extra_info NEEDS TO BE REWRITTEN, SINCE IT'LL REDIRECT TO /SHOP/PAYMENT
            return request.redirect("/shop/extra_info")

        # [REF] /shop/payment

        shipping_partner_id = False
        if order:
            if order.partner_shipping_id.id:
                shipping_partner_id = order.partner_shipping_id.id
            else:
                shipping_partner_id = order.partner_invoice_id.id

        # TODO: ADAPT THIS PART FROM THE ORIGINAL CONTROLLER

        # values = {
        #     'website_sale_order': order
        # }
        # values['errors'] = SaleOrder._get_errors(order)
        # values.update(SaleOrder._get_website_data(order))
        # if not values['errors']:
        #     acquirers = request.env['payment.acquirer'].search(
        #         [('website_published', '=', True), ('company_id', '=', order.company_id.id)]
        #     )
        #     values['acquirers'] = []
        #     for acquirer in acquirers:
        #         acquirer_button = acquirer.with_context(submit_class='btn btn-primary',
        #                                                 submit_txt=_('Pay Now')).sudo().render(
        #             '/',
        #             order.amount_total,
        #             order.pricelist_id.currency_id.id,
        #             values={
        #                 'return_url': '/shop/payment/validate',
        #                 'partner_id': shipping_partner_id,
        #                 'billing_partner_id': order.partner_invoice_id.id,
        #             }
        #         )
        #         acquirer.button = acquirer_button
        #         values['acquirers'].append(acquirer)
        #
        #     values['tokens'] = request.env['payment.token'].search(
        #         [('partner_id', '=', order.partner_id.id), ('acquirer_id', 'in', acquirers.ids)])
        #
        # return request.render("website_sale.payment", values)

        # TODO: CHECK WHETHER ADDRESS IS GIVEN
        #     for f in self._get_mandatory_billing_fields():
        #         if not order.partner_id[f]:
        #             return request.redirect('/shop/address?partner_id=%d' % order.partner_id.id)
        #
        #
            # return {
            #     'success': False,
            # }
        # return {'success': True}


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
