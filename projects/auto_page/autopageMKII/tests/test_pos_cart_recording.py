import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd
from functions.pos.pricing_engine import POSPricingReconciler

USER_HTML_SNIPPET = """
<div class="col-sm-12" id="bodyOfSku" style="padding-left:0px;padding-right: 0px;max-height: 550px;overflow-x: hidden; width: 100%">
    <div ng-repeat="x in posbook.data.dataOfDetail | filter : {status : {lookupMasterId : '!10830004'}}" class="col-sm-12 panel panel-default ng-scope" style="padding-top:0px;padding-bottom:0px;margin-bottom: 5px;">
        <div class="panel-body" style="padding-top:3px;padding-bottom:3px;padding-left: 0px;padding-right: 0px">
            <div class="row col-sm-6">
                <div class="col-sm-2  col-xs-3 text-center" style="padding:0px">
                    <div class="center">
                        <a href="/smartcore/smartinfo/sellingguidesku.htm?productId=76319&amp;productCode=" target="_blank">
                            <img class="imageskudisplay-h1-small" src="/smartcore/images/not-available-small.png">
                        </a>
                    </div>
                </div>
                <div class="col-sm-9 col-xs-8 wrap-text" style="padding:0px">
                    <div class="row ng-scope" ng-if="!x.manualInputFlag">
                        <span ng-click="productNameChangeChk(x)"><a><u class="ng-binding">CO6-011776</u></a></span>
                        <span class="font-color-secondary ng-binding">MSI Modern 15 F13MG-1251TH/i5-1334U/16GB/512GB/UMA/15.6"_FHD/Platinum Gray/Win11/2Y</span>
                        <br>
                        <span class="label ng-binding label-success">SRP</span> <span class="font-color-base ng-binding">25,080.00.-</span>
                    </div>

                    <div class="row ng-scope" ng-repeat="uCoupon in x.dataOfCoupon | uCouponFilter | orderBy: 'couponCode'" style="margin-right:0px; margin-left:0px">
                        <div>
                            <a data-toggle="tooltip" class="font-color-base ng-binding" style="text-decoration: underline">CP2609070007</a><span class="font-color-secondary-red ng-binding"> 300.- </span>
                        </div>
                    </div>
                    <div class="row ng-scope" ng-repeat="uCoupon in x.dataOfCoupon | uCouponFilter | orderBy: 'couponCode'" style="margin-right:0px; margin-left:0px">
                        <div>
                            <a data-toggle="tooltip" class="font-color-base ng-binding" style="text-decoration: underline">CP2609070008</a><span class="font-color-secondary-red ng-binding"> 440.- </span>
                        </div>
                    </div>
                    <div class="row ng-scope" ng-repeat="uCoupon in x.dataOfCoupon | uCouponFilter | orderBy: 'couponCode'" style="margin-right:0px; margin-left:0px">
                        <div>
                            <a data-toggle="tooltip" class="font-color-base ng-binding" style="text-decoration: underline">CP2609100001</a><span class="font-color-secondary-red ng-binding"> 500.- </span>
                        </div>
                    </div>
                    <div class="row ng-scope" ng-repeat="uCoupon in x.dataOfCoupon | uCouponFilter | orderBy: 'couponCode'" style="margin-right:0px; margin-left:0px">
                        <div>
                            <a data-toggle="tooltip" class="font-color-base ng-binding" style="text-decoration: underline">DC2410010001</a><span class="font-color-secondary-red ng-binding"> 700.- </span>
                        </div>
                    </div>
                </div>
            </div>
            <div class="row col-sm-6" style="padding:0px;display: flex;justify-content: space-between;align-content: center;">
                <div class="col-sm-4" style="padding:0px">
                    <div class="row">
                        <span class="col-sm-6 font-color-secondary text-right">Amount :</span>
                        <div class="col-sm-6 text-right">
                            <a class="font-color-base ng-binding ng-scope">25,080.00</a>
                        </div>
                    </div>
                    <div class="row">
                        <span class="col-sm-6 font-color-secondary text-right">Disc. :</span> <span class="col-sm-6 font-color-secondary-red text-right ng-binding">-1,940.00</span>
                    </div>
                    <div class="row">
                        <span class="col-sm-6 font-color-secondary text-right">Total Net:</span>
                        <a class="col-sm-6 text-right font-color-base ng-binding" ng-click="displayPrice(x, $index)">23,140.00 </a>
                    </div>
                </div>
                <div class="col-sm-4 text-center" style="padding:0px">
                    <span class="col-sm-4 ng-binding" style="color:#2a337c; font-size:26px; padding : 0px">1</span>
                </div>
            </div>
            <div class="col-sm-12">
                <div class="row ng-scope" ng-repeat="cdt in x.productCouponDetail|couponauto">
                    <div class="col-sm-9">
                        <span class="font-color-base ng-binding">DC2507220036 NOTEBOOK MSI : BUNDLE MOUSE WISE MT-202</span>
                        <span class="font-color-secondary-red ng-binding">60.-</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <div ng-repeat="x in posbook.data.dataOfDetail | filter : {status : {lookupMasterId : '!10830004'}}" class="col-sm-12 panel panel-default ng-scope" style="padding-top:0px;padding-bottom:0px;margin-bottom: 5px;">
        <div class="panel-body" style="padding-top:3px;padding-bottom:3px;padding-left: 0px;padding-right: 0px">
            <div class="row col-sm-6">
                <div class="col-sm-9 col-xs-8 wrap-text" style="padding:0px">
                    <div class="row ng-scope" ng-if="!x.manualInputFlag">
                        <span ng-click="productNameChangeChk(x)"><a><u class="ng-binding">MNL-001886</u></a></span>
                        <span class="font-color-secondary ng-binding">DAHUA Gaming Monitor Curved LM30-E330CA</span>
                        <br>
                        <span class="label ng-binding label-success">OnlineSHP1</span> <span class="font-color-base ng-binding">7,469.00.-</span>
                    </div>
                    <div class="row ng-scope" ng-repeat="uCoupon in x.dataOfCoupon | uCouponFilter | orderBy: 'couponCode'" style="margin-right:0px; margin-left:0px">
                        <div>
                            <a data-toggle="tooltip" class="font-color-base ng-binding" style="text-decoration: underline">DC2608280030</a><span class="font-color-secondary-red ng-binding"> 1,500.- </span>
                        </div>
                    </div>
                </div>
            </div>
            <div class="row col-sm-6">
                <div class="col-sm-4" style="padding:0px">
                    <div class="row">
                        <span class="col-sm-6 font-color-secondary text-right">Total Net:</span>
                        <a class="col-sm-6 text-right font-color-base ng-binding" ng-click="displayPrice(x, $index)">5,969.00 </a>
                    </div>
                </div>
                <div class="col-sm-4 text-center" style="padding:0px">
                    <span class="col-sm-4 ng-binding" style="color:#2a337c; font-size:26px; padding : 0px">1</span>
                </div>
            </div>
        </div>
    </div>
</div>
"""


class TestPOSCartRecording(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.excel_path = os.path.join(self.temp_dir, "test_cp_data.xlsx")

        # Initial test Excel
        df_init = pd.DataFrame([
            {
                "sku": "CO6-011776",
                "sale_price": 23140.0,
                "cp_name": "MANUAL_CP_TEMPLATE",
                "usage_start_date": "2026-09-01",
                "usage_end_date": "2026-09-30"
            }
        ])
        df_init.to_excel(self.excel_path, index=False)

        self.mock_bot = MagicMock()
        self.mock_app = MagicMock()
        self.mock_driver = MagicMock()

        self.mock_bot.app = self.mock_app
        self.mock_bot.driver = self.mock_driver
        self.mock_bot.wait50 = MagicMock()
        self.mock_bot.cus_order = "240911TESTORDER"

        self.mock_app.cp_table_location = self.excel_path
        self.mock_app.cp_df = df_init
        self.mock_app.cus_order = "240911TESTORDER"
        self.mock_app.is_testing = False

        self.mock_driver.page_source = USER_HTML_SNIPPET

        self.reconciler = POSPricingReconciler(self.mock_bot)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_scrape_pos_cart_items_with_user_snippet(self):
        """ทดสอบการดึงข้อมูล SKU, รายการคูปองทั้งหมด (ทั้ง uCoupon และ auto) และราคาขายสุทธิจาก HTML snippet ที่ผู้ใช้ให้มา"""
        items = self.reconciler.scrape_pos_cart_items()
        self.assertEqual(len(items), 2)

        # SKU 1: CO6-011776
        item1 = items[0]
        self.assertEqual(item1["sku"], "CO6-011776")
        expected_coupons_item1 = "CP2609070007 CP2609070008 CP2609100001 DC2410010001 DC2507220036"
        self.assertEqual(item1["coupons"], expected_coupons_item1)
        self.assertEqual(item1["unit_net"], 23140.0)
        self.assertEqual(item1["qty"], 1.0)

        # SKU 2: MNL-001886
        item2 = items[1]
        self.assertEqual(item2["sku"], "MNL-001886")
        self.assertEqual(item2["coupons"], "DC2608280030")
        self.assertEqual(item2["unit_net"], 5969.0)
        self.assertEqual(item2["qty"], 1.0)

    def test_record_pos_cart_summary_to_excel(self):
        """ทดสอบการบันทึกสรุปรายการออเดอร์ลง cp_data.xlsx: แถวเดิมต้องไม่อัปเดตทับ cp_name และแถวใหม่ถูก append"""
        self.reconciler.record_pos_cart_summary_to_excel("240911TESTORDER")

        # ตรวจสอบไฟล์ Excel ที่ถูกเซฟ
        df_saved = pd.read_excel(self.excel_path)
        self.assertEqual(len(df_saved), 2)

        # ตรวจสอบคอลัมน์ใหม่ที่เพิ่มขึ้น
        for col in ["last_order_id", "last_used_cp", "last_actual_price", "last_updated"]:
            self.assertIn(col, df_saved.columns)

        # ตรวจสอบแถวเดิม CO6-011776
        row1 = df_saved[df_saved["sku"] == "CO6-011776"].iloc[0]
        self.assertEqual(row1["cp_name"], "MANUAL_CP_TEMPLATE")  # cp_name ต้องไม่ถูกเขียนทับ!
        self.assertEqual(str(row1["last_order_id"]), "240911TESTORDER")
        self.assertIn("CP2609070007", row1["last_used_cp"])
        self.assertIn("CP2609100001", row1["last_used_cp"])
        self.assertIn("DC2507220036", row1["last_used_cp"])
        self.assertEqual(row1["last_actual_price"], 23140.0)
        self.assertTrue(pd.notna(row1["last_updated"]) and len(str(row1["last_updated"])) > 0)

        # ตรวจสอบแถวใหม่ MNL-001886 ที่ถูกเพิ่ม
        row2 = df_saved[df_saved["sku"] == "MNL-001886"].iloc[0]
        self.assertEqual(str(row2["last_order_id"]), "240911TESTORDER")
        self.assertEqual(row2["last_used_cp"], "DC2608280030")
        self.assertEqual(row2["last_actual_price"], 5969.0)

        # ตรวจสอบ log bot แจ้งเตือน
        log_calls = [c[0][0] for c in self.mock_app.update_log.call_args_list]
        self.assertTrue(any("บันทึกประวัติออเดอร์" in msg for msg in log_calls))
        self.assertTrue(any("CO6-011776" in msg and "23,140.00" in msg for msg in log_calls))
        self.assertTrue(any("MNL-001886" in msg and "5,969.00" in msg for msg in log_calls))

    def test_reconcile_and_verify_triggers_record_on_success(self):
        """ทดสอบว่าเมื่อ reconcile_and_verify() ผ่าน all_ok=True จะเรียก record_pos_cart_summary_to_excel() อัตโนมัติก่อน finish_order()"""
        self.reconciler.record_pos_cart_summary_to_excel = MagicMock()
        self.mock_bot.ProductManager.auto_add_all_items = MagicMock()
        self.mock_bot.ProductManager.verify_all.return_value = {
            "all_ok": True,
            "qty": {"CO6-011776": {"ok": True, "expected": 1, "actual": 1}},
            "price": {"CO6-011776": {"ok": True, "expected": 23140.0, "actual": 23140.0}}
        }

        self.reconciler.reconcile_and_verify()

        self.reconciler.record_pos_cart_summary_to_excel.assert_called_once_with("240911TESTORDER")
        self.mock_app.finish_order.assert_called_once()


if __name__ == "__main__":
    unittest.main()
