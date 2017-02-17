# -*- coding: utf-8 -*-
# © 2015 bloopark systems (<http://bloopark.de>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import odoo.tests


@odoo.tests.common.at_install(False)
@odoo.tests.common.post_install(True)
class TestUi(odoo.tests.HttpCase):
    def test_01_admin_checkout(self):
        self.phantom_js("/", "odoo.Tour.run('shop_buy_product_oca',"
                             "" "'test')",
                        "odoo.Tour.tours.shop_buy_product_oca",
                        login="admin")

    def test_02_demo_checkout(self):
        self.phantom_js("/", "odoo.Tour.run('shop_buy_product_oca', "
                             "'test')",
                        "odoo.Tour.tours.shop_buy_product_oca",
                        login="demo")

    def test_03_public_checkout(self):
        self.phantom_js("/", "odoo.Tour.run('shop_buy_product_oca', "
                             "'test')",
                        "odoo.Tour.tours.shop_buy_product_oca")
