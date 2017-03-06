/**
 * Created by administrator on 14/02/2017.
 */
odoo.define("website_sale_one_step_checkout", function (require) {
    "use strict";

    var ajax = require('web.ajax');
    var base = require('web_editor.base');
    var core = require("web.core");

    var _t = core._t;
    //Todo remove?
    // var website = require('website.website');
    
  function getPostAddressFields(elms, data) {
        elms.each(function(index) {
            data[$(this).attr('name')] = $(this).val();
        });
        return data;
  };

  function validateModalAddress(){
      var billingElems = $('#osc_billing input, #osc_billing select')
          , data = {};

      data = getPostAddressFields(billingElems, data);

      // FOR VALIDATION WE NEED submitted
      data.submitted = true;

      $('.oe_website_sale_osc .has-error').removeClass('has-error');

      ajax.jsonRpc('/shop/checkout/render_address/', 'call', data)
          .then(function (result) {
              if (result.success) {
                  $('#js_confirm_address').attr("disabled", false);

                  // Update frontend address view
                  $('#col-1').html(result.template)

                  // Re-enable JS event listeners
                  $('.js-billing-address .js_edit_address').on('click', editBilling);
                  $('.js-shipping-address .js_edit_address').on('click', editShipping);
                  $("#add-shipping-address").on('click', 'a', addShipping);
                  changeShipping();

                  // hide Modal
                  $('#address-modal').modal('hide');
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

  function startTransaction(acquirer_id){
      ajax.jsonRpc('/shop/payment/transaction/' + acquirer_id, 'call', {}).then(function (data) {
          $(data).appendTo('body').submit();
      });
      return false;
  }

  function validateAddressForm(){
      return ajax.jsonRpc('/shop/checkout/validate_address_form', 'call', {}).then(function (result){
         if(result.success){
             return result;
         } else{
             editBilling(result);
             return result;
         }
      });
  }

  // For Public User
  function addPublicUserAddress() {
      // If the user leaves the modal after a wrong input and
      // and opens the add-billing-address modal, those
      // fields will be still highlighted red.
      removeErrors();

      var title = 'Billing Address';

      var data = {
          'title':_t(title),
      };

      renderModal(data);
  }

  function renderModal(data){
      // Render address template into modal body
      // Params: data, containing partner_id in case of edit event

      ajax.jsonRpc('/shop/checkout/render_address/', 'call', data)
          .then(function(result) {
              $('#address-modal').modal('show');
              if(result.success) {
                  console.log('inserting title');
                  $('#address-modal .modal-header h4').html(data.title);
                  $('#address-modal .modal-body').html(result.template);

                  // Display states if existent for selected country, e.g. US
                  $("select[name='country_id']").change();

              }
          });
  }

  function removeErrors(){
      // If the user leaves the modal after a wrong input and
      // and opens the add-billing-address modal, those
      // fields will be still highlighted red.
      $('.oe_website_sale_osc .has-error').removeClass('has-error');
  }


  function changeShipping(){
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
  }

  // Edit Billing Address
  function editBilling(result) {
        // If the user leaves the modal after a wrong input and
        // and opens the add-billing-address modal, those
        // fields will be still highlighted red.
        removeErrors();

        var title = 'Billing Address';
        var partner_id;

        if(result.partner_id) {
            // This argument will be
            // returned by the controller validate_address_form
            // after its call from the validateAddressForm JS function below.
            // It's necessary in the situation where there exist
            // a name and e-mail from the sign-up procedure, but no
            // further mandatory billing data. This will trigger the
            // modal in "Edit Billing Address" mode.
            partner_id = result.partner_id;
        } else{
            partner_id = $(this).siblings('form').find('input[name=partner_id]').val();
        }

        var data = {
                'title': _t(title),
                'partner_id':partner_id,
            };

        renderModal(data);
  }

  // Edit Shipping Address
  function editShipping () {
        // If the user leaves the modal after a wrong input and
        // and opens the add-billing-address modal, those
        // fields will be still highlighted red.
        $('.oe_website_sale_osc .has-error').removeClass('has-error');

        var title = 'Shipping Address';
        var partner_id = $(this).siblings('form').find('input[name=partner_id]').val();

        var data = {
            'title': _t(title),
            'partner_id':partner_id,
        };

        renderModal(data);
  }

   // Add New Shipping Address
  function addShipping() {
        // If the user leaves the modal after a wrong input and
        // and opens the add-billing-address modal, those
        // fields will be still highlighted red.
        $('.oe_website_sale_osc .has-error').removeClass('has-error');

        var title = 'Shipping Address';
        var data = {
            'title':_t(title),
        };

        renderModal(data);
  }

  base.dom_ready.done(function () {
      // Check whether all mandatory billing fields
      // contain data. If not, open address modal
      validateAddressForm();

      // activate listener
      changeShipping()

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

      // when clicking checkout submit button validate address data first
      // if all is fine trigger payment transaction
      $('#col-3 .js_payment').on('click', 'form button[type=submit]', function (ev) {
          ev.preventDefault();
          ev.stopPropagation();

          // TODO is return necessary?
          validateAddressForm()
          .then(function (result) {
              if(result.success){
                  // proceed to payment transaction
                  ajax.jsonRpc('/shop/checkout/proceed_payment/', 'call', {});
                  return true;
              } else{
                  return false;
                  // do nothing, address modal in edit mode
                  // will be opened instead
              }
          })
              .then( function (result){
                  if(result){
                      var $form = $(ev.currentTarget).parents('form');
                      // TODO WHAT HAPPENS IF USER MESSES WITH THE ACQUIRER_ID
                      var acquirer_id = $(ev.currentTarget).parents('div.oe_sale_acquirer_button').first().data('id');
                      if (! acquirer_id ){
                          return false;
                      }
                      $form.off('submit')
                      startTransaction(acquirer_id);
                  }
              });


          return false;
      });

      // Automatically open modal in 'Billing address' mode for public user
      $('#add-public-user-address').on('click', addPublicUserAddress);
      // Editing Billing Address
      $('.js-billing-address .js_edit_address').on('click', editBilling);

      // Editing shipping address
      $('.js-shipping-address .js_edit_address').on('click', editShipping);

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

      $('#address-modal').on('click', '#js_confirm_address', function(ev){
          ev.preventDefault();
          ev.stopPropagation();
              // Upon confirmation, validate data.
              validateModalAddress();

              return false;
      });


      // END DOM


  });

});