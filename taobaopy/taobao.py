#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TaoBao Python SDK
~~~~~~~~~~~~~~~~~~~~~

usage:

   >>> from taobaopy.taobao import TaoBaoAPIClient
   >>> cli_ = TaoBaoAPIClient("__YOUR_APP_KEY__", "__YOUR_APP_SECRET__")
   >>> r = cli_.tbk_item_get(q="女装", fields="num_iid,title,pict_url,small_images,zk_final_price")
   >>> print(r)
"""

__author__ = 'Fred Wang (taobao-pysdk@1e20.com)'
__title__ = 'taobaopy'
__license__ = 'BSD License'
__copyright__ = 'Copyright 2013-2018 Fred Wang'

import hashlib
import json
import time
import hmac
import logging
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import six

TB_LOG = logging.getLogger(__name__)
TB_LOG.addHandler(logging.NullHandler())

RETRY_SUB_CODES = {
    'isp.top-remote-connection-timeout',
    'isp.top-remote-connection-timeout-tmall',
    'isp.top-remote-service-unavailable',
    'isp.top-remote-service-unavailable-tmall',
    'isp.top-remote-connection-control-error',
    'isp.top-remote-connection-control-error-tmall',
    'isp.top-remote-unknown-error',
    'isp.top-remote-unknown-error-tmall',
    'isp.remote-connection-error',
    'isp.remote-connection-error-tmall',
    'isp.item-update-service-error:GENERIC_FAILURE',
    'isp.item-update-service-error:IC_SYSTEM_NOT_READY_TRY_AGAIN_LATER',
    'ism.json-decode-error',
    'ism.demo-error',
    'isp.service-error',
}


def ensure_binary(value):
    """用于py2 py3兼容，确保是已编码格式"""
    if isinstance(value, six.text_type):
        return value.encode(encoding="utf-8")
    return value


def ensure_text(value):
    """用于py2 py3兼容，确保是未编码格式"""
    if isinstance(value, six.binary_type):
        return str(value)
    return value


def seek_files(files):
    """将所有的文件指针指回到开始"""
    for file_ in files:
        file_.seek(0)


def requests_retry_session(
        retries=3,
        backoff_factor=0.3,
        status_forcelist=(500, 502, 504),
        session=None,
):
    """生成配置过的重试机制的request.Session"""
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=frozenset(['POST', 'GET']),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def default_value_to_str(val):
    """强制转换成string"""
    return str(val)


VALUE_TO_STR = {
    type(datetime(year=2018, month=1, day=1)): lambda v: v.strftime('%Y-%m-%d %H:%M:%S'),
    type('a'): ensure_text,
    type(0.1): lambda v: "%.2f" % v,
    type(True): lambda v: str(v).lower(),
}


class BaseAPIRequest(object):
    """The Base API Request"""

    def __init__(self, url, client, values):
        self.url = url
        self.values = values
        self.client = client
        self.key = client.client_id
        self.sec = client.client_secret
        self.retry_sub_codes = client.retry_sub_codes

    def sign(self):
        """Return encoded data and files
        """
        data, files = {}, {}
        if not self.values:
            raise NotImplementedError('no values')
        args = {'app_key': self.key, 'sign_method': 'hmac', 'format': 'json', 'v': '2.0', 'timestamp': datetime.now()}

        for key, val in list(dict(self.values, **args).items()):
            new_key = key.replace('__', '.')
            if hasattr(val, 'read'):
                files[new_key] = val
            elif val is not None:
                data[new_key] = VALUE_TO_STR.get(type(val), default_value_to_str)(val)

        args_str = "".join(["{}{}".format(k, data[k]) for k in sorted(data.keys())])
        sign = hmac.new(ensure_binary(self.sec), ensure_binary(args_str), digestmod=hashlib.md5)

        data['sign'] = sign.hexdigest().upper()
        return data, files

    def run(self):
        """执行http操作调用API"""
        data, files = self.sign()
        ret = {}

        # prepared data for logging
        method = data.get('method', '')
        input_args = json.dumps(dict(data, **dict([(k, str(v)) for k, v in six.iteritems(files)])), ensure_ascii=False)

        def do_log(request):
            """一次普通的不带重试的请求"""
            output_args = json.dumps(request, ensure_ascii=False)
            log_data = '[TOP_API_CALL] {ts_used:2f}ms |xxx| {method} |xxx| {input_args} |xxx| {output_args}'.format(
                ts_used=ts_used, method=method, input_args=input_args, output_args=output_args)

            if 'error_response' in request:
                TB_LOG.warning(log_data)
            elif method.startswith("taobao.ump") or method.startswith("taobao.promotion"):
                TB_LOG.info(log_data)
            else:
                TB_LOG.debug(log_data)

        for try_id in range(self.client.retry_count):
            seek_files(list(files.values()))

            ts_used = 0.0
            ts_start = time.time()
            ret = self.open(data, files)
            ts_used = (time.time() - ts_start) * 1000
            do_log(ret)

            if 'error_response' in ret:
                sub_code = ret['error_response'].get('sub_code')
                if sub_code in self.retry_sub_codes:
                    continue
                elif sub_code in {'accesscontrol.limited-by-api-access-count', 'isp.call-limited'}:
                    if try_id < self.client.retry_count - 1:
                        TB_LOG.warning("meet access-control, sleep 1 seconds")
                        time.sleep(1)
                    continue
            break

        if 'error_response' in ret:
            error_resp = ret['error_response']
            raise TaoBaoAPIError(data, **error_resp)

        return ret

    def open(self, data, files):
        """需要被继承的class实现的函数，可以自定义http的客户端"""
        raise NotImplementedError("open function should be implemented")


class DefaultAPIRequest(BaseAPIRequest):
    """The Basic API Request"""

    def __init__(self, url, client, values):
        super(DefaultAPIRequest, self).__init__(url, client, values)
        self._session = None

    @property
    def session(self):
        """初始化一个session实例，可以复用"""
        if not self._session:
            self._session = requests_retry_session()
        return self._session

    def open(self, data, files):
        """默认的open函数，使用requests"""
        seek_files(files.values())

        if not files:
            timeout = 5
        else:
            timeout = 20

        default_headers = {'Accept-Encoding': 'gzip', 'Connection': 'close'}
        resp = self.session.post(self.url, data, files=files, headers=default_headers, timeout=timeout)

        try:
            return resp.json()
        except ValueError:
            try:
                text = resp.text.replace('\t', '\\t').replace('\n', '\\n').replace('\r', '\\r')
                return json.loads(text)
            except ValueError as err:
                return {
                    "error_response": {
                        "msg": "json decode error",
                        "sub_code": "ism.json-decode-error",
                        "code": 15,
                        "sub_msg": "json-error: %s || %s" % (str(err), resp.text)
                    }
                }


class TaoBaoAPIError(Exception):
    """raise APIError if got failed json message."""

    def __init__(self, request, code='', msg='', sub_code='', sub_msg='', request_id='', **kwargs):
        """TaoBao SDK Error, Raised From TaoBao"""
        # pylint: disable=too-many-arguments
        self.request = request
        self.code = code
        self.msg = msg
        self.sub_code = sub_code
        self.sub_msg = sub_msg
        self.request_id = request_id
        self.kwargs = kwargs
        Exception.__init__(self, self.__str__())

    def __repr__(self):
        return "{code}|{msg}|{sub_code}|{sub_msg}|{request_id}|{request}".format(
            code=self.code, msg=self.msg, sub_code=self.sub_code, sub_msg=self.sub_msg, request_id=self.request_id, request=self.request)

    def __str__(self):
        """Build String For All the Request and Response"""
        return "{code}|{msg}|{sub_code}|{sub_msg}|{request_id}".format(
            code=self.code, msg=self.msg, sub_code=self.sub_code, sub_msg=self.sub_msg, request_id=self.request_id)

    def str2(self):
        """Build String For the Request only"""
        return "{code}|{msg}|{sub_code}|{sub_msg}|{request_id}".format(
            code=self.code, msg=self.msg, sub_code=self.sub_code, sub_msg=self.sub_msg, request_id=self.request_id)


class HttpObject(object):
    """根据函数名组装http请求"""

    # pylint: disable=too-few-public-methods
    def __init__(self, client):
        self.client = client

    def __getattr__(self, attr):
        def wrap(**kw):
            """根据函数名组装请求参数"""
            if attr.find('__') >= 0:
                attr2 = attr.split('__', 2)
                method = attr2[0] + '.' + attr2[1].replace('_', '.')
            else:
                method = "taobao." + attr.replace('_', '.')
            kw['method'] = method
            if not self.client.is_expires():
                kw['session'] = self.client.access_token
            req = self.client.fetcher_class(self.client.gw_url, self.client, kw)
            return req.run()

        return wrap


class TaoBaoAPIClient(object):
    """API client using synchronized invocation."""

    # pylint: disable=too-many-instance-attributes
    # Eight is reasonable in this case.
    def __init__(self, app_key, app_secret, domain='https://eco.taobao.com', fetcher_class=DefaultAPIRequest, retry_sub_codes=None, retry_count=5, **kwargs):
        """Init API Client"""
        # pylint: disable=too-many-arguments
        self.client_id = app_key
        self.client_secret = app_secret
        # support http and https prefix, do not add suffix slash(/)
        if domain.startswith("http://") or domain.startswith("https://"):
            self.gw_url = '%s/router/rest' % (domain, )
        else:
            self.gw_url = 'http://%s/router/rest' % (domain, )
        self.access_token = None
        self.expires = 0.0
        self.fetcher_class = fetcher_class
        self.get = HttpObject(self)
        self.post = HttpObject(self)
        self.upload = HttpObject(self)
        self.retry_sub_codes = RETRY_SUB_CODES | (retry_sub_codes or set())
        self.retry_count = retry_count
        self.kwargs = kwargs

    def set_access_token(self, access_token, expires_in=2147483647):
        """Set Default Access Token To This Client"""
        self.access_token = str(access_token)
        self.expires = float(expires_in)

    def set_fetcher_class(self, fetcher_class):
        """Set Fetcher Class"""
        self.fetcher_class = fetcher_class

    def is_expires(self):
        """Check Token expires"""
        return not self.access_token or time.time() > self.expires

    def __getattr__(self, attr):
        return getattr(self.post, attr)


APIClient = TaoBaoAPIClient
APIError = TaoBaoAPIError
