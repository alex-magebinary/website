odoo.define("website_sale_one_step_checkout.tour_shop", function (require) {
    "use strict";

    var core = require("web.core");
    var tour = require("web_tour.tour");
    var base = require("web_editor.base");

    var _t = core._t;
    console.log('tour register');
    tour.register('shop_buy_product_oca', {

        // name: "Try to buy products with one step checkout",
        url: '/shop',
        test: true,
        wait_for: base.ready(),
        },
        [
            {
                // step 0
                content: _t("select iPad Mini"),
                trigger: 'a[itemprop="name"][href*="ipad-mini"]',
                // position: "bottom",
            }, {
                //step 1
                content: _t("click on add to cart"),
                trigger: '#add_to_cart',
                // position: 'bottom',
            }, {
                //step 2
                content:    _t("go to checkout"),
                trigger: 'a[href="/shop/checkout"]',
            }, {
                //step 3
                content:     _t("test with input error"),
                trigger:   'form[action="/payment/transfer/feedback"] .btn[type="submit"]',
                onload: function (tour) {
                    $("input[name='phone']").val("");
                }
            }, {
                //step 5
                content:     _t("test without input error"),
                waitFor:   'div[id="osc_billing"] .has-error',
                trigger:   'form[action="/payment/transfer/feedback"] .btn[type="submit"]',
                onload: function (tour) {
                    if ($("input[name='name']").val() === "")
                        $("input[name='name']").val("website_sale-test-shoptest");
                    if ($("input[name='email']").val() === "")
                        $("input[name='email']").val("website_sale_test_shoptest@websitesaletest.optenerp.com");
                    $("input[name='phone']").val("123");
                    $("input[name='street']").val("xyz");
                    $("input[name='city']").val("Magdeburg");
                    $("input[name='zip']").val("39104");
                    $("select[name='country_id']").val("11");
                },
            }, {
                //step 6
                content:     _t("finish"),
                waitFor:   '.oe_website_sale:contains("Thank you for your order")',
            }
        ]
    );
});