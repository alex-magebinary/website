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

  function validateModalAddress(ev){
      var billingElems = $('#osc_billing input, #osc_billing select')
          , data = {};

      data = getPostAddressFields(billingElems, data);

    //   if ($('#osc_billing select[name=shipping_id]').val() == '-1') {
    //   data = getPostAddressFields(shippingElms, data);
    // }
    //
    // if (paymentElms.length) {
    //   data = getPostAddressFields(paymentElms, data);
    //   data['payment_data'] = true;
    // }

      $('.oe_website_sale_osc .has-error').removeClass('has-error');
    ajax.jsonRpc('/shop/checkout/validate_address/', 'call', data)
      .then(function (result) {
          console.log(result);
          if (result.success) {
            $('#js_confirm_address').attr("disabled", false);
            $('#address').modal('hide');
            console.log('pre-render');
            $('#add-billing-address').after(result.template);
            $('#add-shipping-address').after(result.template);
            console.log('post-render')
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

  // function validate(){
  //     console.log("Validating forms");
  //         if ($(".oe_website_sale_osc input[name='name']").val().length   >   0   &&
  //             $(".oe_website_sale_osc input[name='email']").val().length  >   0   &&
  //             $(".oe_website_sale_osc input[name='phone']").val().length  >   0   &&
  //             $(".oe_website_sale_osc input[name='street']").val().length  >  0   &&
  //             $(".oe_website_sale_osc input[name='city']").val().length  >    0   &&
  //             $(".oe_website_sale_osc input[name='zip']").val().length  >     0   &&
  //             $(".oe_website_sale_osc select[name='country_id']").val().length  >   0) {
  //               console.log("all full now. that's what she said");
  //               console.log($('#js_confirm_address'));
  //               $('#js_confirm_address').attr("disabled", false);
  //
  //         } else {
  //             console.log("not true yet. need to fill out more");
  //             $('#js_confirm_address').attr("disabled", true);
  //         }
  // };


  function validateAddress(ev) {
        //Todo: this is now just preliminary to set the last_order_id.
      ajax.jsonRpc('/shop/checkout/confirm_address/', 'call');//, data);
    };

  function startTransaction(acquirer_id, form){
    form.off('submit');
      ajax.jsonRpc('/shop/payment/transaction/' + acquirer_id, 'call', {}).then(function (data) {
          $(data).appendTo('body').submit();
      });
      return false;
  };

  //
  base.dom_ready.done(function () {

      // when choosing an delivery carrier, update the total prices
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


      // when clicking checkout submit button validate address data,
      // if all is fine form submit will be done in validate function because of
      // ajax call
      $('#col-3 .js_payment').on('click', 'form button[type=submit]', function (ev) {
          ev.preventDefault();
          ev.stopPropagation();
          // validate address and set last_order_id
          validateAddress(ev);
          var $form = $(ev.currentTarget).parents('form');
          var acquirer_id = $(ev.currentTarget).parents('div.oe_sale_acquirer_button').first().data('id');
          startTransaction(acquirer_id, $form);
          return false;
      });

      //var confirmButton = $('#js_confirm_address form button[type=submit]');
      //validate();
      //$("input[name='name'], input[name='email'], input[name='phone'], input[name='street'], input[name='city'], input[name='zip'], select[name='country_id']").change(validate);
      // default state is deactivated checkbox and disabled submit button
      //confirmButton.attr('disabled', 'disabled');



    $('#js_confirm_address').on('click', function(ev) {
      ev.preventDefault();
      ev.stopPropagation();
      validateModalAddress(ev);
      return false;
    });




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
  });

});