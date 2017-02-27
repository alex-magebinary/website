/**
 * Created by administrator on 14/02/2017.
 */
odoo.define("website_sale_osc", function (require) {
    "use strict";

    var ajax = require('web.ajax');
    var base = require('web_editor.base');
    var website = require('website.website');

    function changeDelivery(carrierId) {
    ajax.jsonRpc('/shop/checkout/change_delivery', 'call', {'carrier_id': carrierId})
      .then(function (result) {
        if (result) {
          if (result.success) {
            if (result.order_total) {
                $('#order_total .oe_currency_value').text(result.order_total);
              $('.js_payment input[name=amount]').val(result.order_total);
            }
            if (result.order_total_taxes) {
                $('#order_total_taxes .oe_currency_value').text(result.order_total_taxes);

            }
            if (result.order_total_delivery) {
                $('#order_delivery .oe_currency_value').text(result.order_total_delivery);

            }
          } else if (result.errors) {
            // ???
          }
        } else {
          // ???
          window.location.href = '/shop';
        }
      });

  }

  function getPostAddressFields(elms, data) {
        elms.each(function(index) {
            data[$(this).attr('name')] = $(this).val();
        });


        return data;
  };

  function validateModalAddress(mode){
      var billingElems = $('#osc_billing input, #osc_billing select')
          , data = {};

      data = getPostAddressFields(billingElems, data);

      // FOR VALIDATION WE NEED submitted
      data.submitted = true;
      // IN CASE WE CREATE NEW BILLING ADDRESS WE NEED mode
      data.mode = mode;

      $('.oe_website_sale_osc .has-error').removeClass('has-error');
      alert("validate address");

      ajax.jsonRpc('/shop/checkout/render_address/', 'call', data)
          .then(function (result) {
              console.log(result);
              if (result.success) {
                  alert("result successful");
                  $('#js_confirm_address').attr("disabled", false);
                  $('#address-modal').modal('hide');
            // TODO: Once first address is created what happens to:
            //  if order.partner_id.id == request.website.user_id.sudo().partner_id.id:

                  // TODO ACTIVATE JS FOR NEWLY INSERTED VIEWS
                  if(result.mode[1] == 'shipping'){
                          // Update Shippings view
                          $('.js-shipping-address').html(result.template);

                          // Re-enable JS eventlisteners
                          $('.js-shipping-address .js_edit_address').on('click', editShipping);
                          $("#add-shipping-address").on('click', 'a', addShipping);

                  } else{
                      // Update Billings view
                      $('.js-billing-address').html(result.template);
                      adjustBillingButtons();


                      // Re-enable JS event listeners
                      $('.js-billing-address .js_edit_address').on('click', editBilling);
                      $("#add-billing-address").on('click', 'a', addBilling);
                      }
                  // TODO: REF
              // if(result.mode[1] == 'billing') {
              //     $('#add-billing-address').after(result.template);
              //
              //     $('#add-shipping-address').after(result.template);
              // } else {
              //     $('#add-shipping-address').after(result.template);
              // }
                  return false;
          } else if (result.errors) {
            for (var key in result.errors) {
              if ($('.oe_website_sale_osc input[name=' + key + ']').length > 0) {
                $('.oe_website_sale_osc input[name=' + key + ']').parent().addClass('has-error');
              } else if ($('.oe_website_sale_osc select[name=' + key + ']').length > 0) {
                $('.oe_website_sale_osc select[name=' + key + ']').parent().addClass('has-error');
              }
            }
          } else {
          // ???
          window.location.href = '/shop';
        }

      });
  }


  function validateCheckout() {
        //Todo: this is now just preliminary to set the last_order_id.
      alert('Validate Checkout');
      ajax.jsonRpc('/shop/checkout/validate_checkout/', 'call', {});
    };

  function startTransaction(acquirer_id){
     // TODO UPDATE THIS
      // form.off('submit');
      alert("start Transaction with acquirer id: ", acquirer_id);
      ajax.jsonRpc('/shop/payment/transaction/' + acquirer_id, 'call', {}).then(function (data) {
          alert('back to JS, data:');
          console.log(data);
          $(data).appendTo('body').submit();
      });
      return false;
  }
    function renderAddressTemplate(data){
      // Render address template into modal body
      // Params: data, consisting of mode and partner_id
      // if there is any. Depends on type of event.
      console.log(data);
      ajax.jsonRpc('/shop/checkout/render_address/', 'call', data)
          .then(function(result) {
              if(result.success) {
                  $('#address-modal').modal();

                  $('#address-modal .modal-header h4').html(data.title);
                  $('#address-modal .modal-body').html(result.template);
                      // TODO for logged in users 5 of .modal-backdrop divs get created
                    // TODO which make the background turn black upon modal activation
                    // TODO FIX IT
                  //$(".modal-backdrop in").remove(); // bootstrap leaves a modal-backdrop
                  $('#js_confirm_address').on('click', function(ev){
                      ev.preventDefault();
                      ev.stopPropagation();

                      // Upon confirmation, validate data.
                      // Forward mode to controller in case of Add New Billing Address event
                      validateModalAddress(data.mode);
                      return false;
                  });
                  return false;
              }
          })
  }

  function removeErrors(){
        $('.oe_website_sale_osc .has-error').removeClass('has-error');
  }

  // from website_sale.js
  $('#osc_shipping').on('click', '.js_change_shipping', function() {
          if (!$('body.editor_enable').length) { //allow to edit button text with editor
            var $old = $('.all_shipping').find('.panel.border_primary');
            $old.find('.btn-ship').toggle();
            $old.addClass('js_change_shipping');
            $old.removeClass('border_primary');

            var $new = $(this).parent('div.one_kanban').find('.panel');
            $new.find('.btn-ship').toggle();
            $new.removeClass('js_change_shipping');
            $new.addClass('border_primary');

            var $form = $(this).parent('div.one_kanban').find('form.hide');
            $.post($form.attr('action'), $form.serialize()+'&xhr=1');
          }
  });

  // from website_sale.js
  $('#osc_billing').on('click', '.js_change_billing', function() {
          if (!$('body.editor_enable').length) { //allow to edit button text with editor
            var $old = $('.all_billing').find('.panel.border_primary');
            $old.find('.btn-bill').toggle();
            $old.addClass('js_change_billing');
            $old.removeClass('border_primary');

            // alert('customizing billing buttons');
            // $replace.find('.btn-ship').addClass('btn-bill').removeClass('btn-ship');
            // $replace.find('.js_change_shipping').addClass('js_change_billing').removeClass('js_change_shipping');



            var $new = $(this).parent('div.one_kanban').find('.panel');
            $new.find('.btn-bill').toggle();
            $new.removeClass('js_change_billing');
            $new.addClass('border_primary');


            var $form = $(this).parent('div.one_kanban').find('form.hide');
            $.post($form.attr('action'), $form.serialize()+'&xhr=1');
             //$new.find('.btn-primary').text("Current billing address");
          }
  });

  // Edit Billing Address
  function editBilling() {
        // If the user leaves the modal after a wrong input and
        // and opens the add-billing-address modal, those
        // fields will be still highlighted red.
        removeErrors();

        var title = 'Billing Address';
        var partner_id = $(this).siblings('form').find('input[name=partner_id]').val();
        alert(partner_id);

        var data = {
            'title':title,
            'partner_id':partner_id,
            'mode':['edit', 'billing']
        };

        renderAddressTemplate(data);
  }

  // Edit Shipping Address
  function editShipping () {
        // If the user leaves the modal after a wrong input and
        // and opens the add-billing-address modal, those
        // fields will be still highlighted red.
        $('.oe_website_sale_osc .has-error').removeClass('has-error');

        var title = 'Shipping Address';
        var partner_id = $(this).siblings('form').find('input[name=partner_id]').val();
        alert(partner_id);

        var data = {
            'title':title,
            'partner_id':partner_id,
            'mode':['edit', 'shipping']
        };

        renderAddressTemplate(data);
        return false;
  }
    // Add new Billing Address
   function addBilling () {
        // If the user leaves the modal after a wrong input and
        // and opens the add-shipping-address modal, those
        // fields will be still highlighted red.
        $('.oe_website_sale_osc .has-error').removeClass('has-error');



        // additional required fields?? See template website_sale.address , line 1254
        $('input[name=field_required]').val('phone,name');

        var title = 'Billing Address';
        var data = {
            'title':title,
            'mode': ['new', 'billing']
        };

        renderAddressTemplate(data);

        // TODO for logged in users 5 of .modal-backdrop divs get created
        // TODO which make the background turn black upon modal activation
        // TODO FIX IT
        $(".modal-backdrop.in").remove(); // bootstrap leaves a modal-backdrop
   }

   // Add New Shipping Address
  function addShipping() {
        // If the user leaves the modal after a wrong input and
        // and opens the add-billing-address modal, those
        // fields will be still highlighted red.
        $('.oe_website_sale_osc .has-error').removeClass('has-error');

        var title = 'Shipping Address';
        var data = {
            'title':title,
            'mode': ['new', 'shipping']
        };

        renderAddressTemplate(data);
  }

  function adjustBillingButtons(){
       var $replace = $('.all_billing');
            $replace.find('.btn-ship').addClass('btn-bill').removeClass('btn-ship');
            $replace.find('.js_change_shipping').addClass('js_change_billing').removeClass('js_change_shipping');
            $replace.find('.btn-primary').html('<i class="fa fa-check"></i>Current billing address');
            
  }


  base.dom_ready.done(function () {
      adjustBillingButtons();

      // when choosing a delivery carrier, update the total prices
      // original part in website_sale_delivery.js uses `delivery_carrier`
      // since we don't want that JS triggered, we're using our own id `delivery_carrier_osc
      // to avoid the page reload of the original one
      var $carrier = $('#delivery_carrier_osc');
      $carrier.find('input[name="delivery_type"]').click(function (ev) {
          var carrierId = $(ev.currentTarget).val();
          changeDelivery(carrierId);
      });

      // when choosing an acquirer, display its order now button
      var $payment = $('#payment_method');
      $payment.on('click', 'input[name="acquirer"]', function (ev) {
          var payment_id = $(ev.currentTarget).val();
          $('div.oe_sale_acquirer_button[data-id]').addClass('hidden');
          $('div.oe_sale_acquirer_button[data-id="' + payment_id + '"]').removeClass('hidden');
      }).find('input[name="acquirer"]:checked').click();

      // terms and conditions
      var terms = $('input[name=terms_conditions]')
          , formButton = $('.js_payment form button[type=submit]');
      if (terms.length) {
          // default state is deactivated checkbox and disabled submit button
          formButton.attr('disabled', 'disabled');
          terms.attr('checked', false);
          terms.click(function () {
              if (terms.is(':checked')) {
                  formButton.attr('disabled', false);
              } else {
                  formButton.attr('disabled', true);
              }
          });
      }

      // TODO: UPDATE
      // when clicking checkout submit button validate address data,
      // if all is fine form submit will be done in validate function because of
      // ajax call
      $('#col-3 .js_payment').on('click', 'form button[type=submit]', function (ev) {
          ev.preventDefault();
          ev.stopPropagation();
          // validate address and set last_order_id
          validateCheckout();
          // var $form = $(ev.currentTarget).parents('form');
          // TODO IS THIS SAVE?
          var acquirer_id = $(ev.currentTarget).parents('div.oe_sale_acquirer_button').first().data('id');
          startTransaction(acquirer_id);
          return false;
      });


    // Editing Billing Address
    $('.js-billing-address .js_edit_address').on('click', editBilling);


    // Editing shipping address
    $('.js-shipping-address .js_edit_address').on('click', editShipping);

    // ADD NEW BILLING ADDRESS
    $("#add-billing-address").on('click', 'a', addBilling);

    // ADD NEW SHIPPING ADDRESS
    $("#add-shipping-address").on('click', 'a', addShipping);

    // Opens modal view when clicking on terms and condition link in
    // onestepcheckout, it loads terms and conditions page and render only wrap
    // container content in modal body
    $('.checkbox-modal-link').on('click', 'a', function(ev) {
      var elm   = $(ev.currentTarget)
        , title = elm.attr('title')
        , page  = elm.attr('data-page-id');

      $.get(page, function (data) {
        var modalBody = $(data).find('main .oe_structure').html();
        if (title) {
          $('#checkbox-modal .modal-header h4').text(title);
        }
        if (!modalBody) {
          modalBody = '<div class="container"><div class="col-md-12"><p>Informationen text</p></div></div>';
        }
        $('#checkbox-modal .modal-body').html(modalBody);
        $('#checkbox-modal').modal();
        return false;
      });
    });

    // END DOM
  });

});