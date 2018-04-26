# coding:utf8
import os
import unittest

from taobaopy.taobao import TaoBaoAPIClient, TaoBaoAPIError


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
        r = self.client.tbk_item_get(q="女装", fields="num_iid,title,pict_url,small_images,zk_final_price", page_size=2)
        self.assertEqual(list(r.keys()), ["tbk_item_get_response"])

    def test_error_response(self):
        try:
            self.client.tbb_abcd(q="abc")
        except TaoBaoAPIError as e:
            self.assertEqual(e.code, 22)

    def test_error_response2(self):
        try:
            self.client.ump_tools_get(q="abc")
        except TaoBaoAPIError as e:
            self.assertEqual(e.code, 11)


if __name__ == '__main__':
    import logging
    logger = logging.getLogger('taobaopy.taobao')
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    unittest.main()
