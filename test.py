# coding:utf8
import os
import unittest

from taobaopy.taobao import TaoBaoAPIClient


class TestTaobaoSDK(unittest.TestCase):
    def setUp(self):
        key = os.getenv("TAOBAO_APP_KEY")
        sec = os.getenv("TAOBAO_APP_SEC")
        self.assertNotEqual(key, None)
        self.assertNotEqual(sec, None)
        self.client = TaoBaoAPIClient(key, sec)

    def test_time_get(self):
        r = self.client.time_get()
        self.assertEqual(list(r.keys()), ["time_get_response"])

    def test_tbk_item_get(self):
        r = self.client.tbk_item_get(q="女装", fields="num_iid,title,pict_url,small_images,zk_final_price")
        self.assertEqual(list(r.keys()), ["tbk_item_get_response"])


if __name__ == '__main__':
    unittest.main()
