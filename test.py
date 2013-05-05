import sys
from taobaopy.taobao import *
import config
import logging.config


def test():
    key = config.key
    sec = config.sec
    token = config.token
    if key[:3] == 'put':
        print "Please put your appkey,appsec and test key in config.py"
        sys.exit(1)
    client = APIClient(key, sec)
    NUM_IID = config.num_iid
    print client.item_get(num_iid=NUM_IID, fields='num_iid,title')
    print client.item_img_upload(num_iid=NUM_IID, is_major='true', image=open("logo.png", "rb"), session=token)
    try:
        print client.item_img_upload(num_iid=NUM_IID, is_major='true', image=open("logo.png", "rb"))
    except APIError, e:
        print e.__str__()


if __name__ == '__main__':
    logging.config.fileConfig('logging.ini')
    test()
 
