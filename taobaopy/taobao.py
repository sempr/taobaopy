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
__version__ = '5.0.2'
__license__ = 'BSD License'
__copyright__ = 'Copyright 2013-2018 Fred Wang'

import hashlib
import json
import time
import hmac
import math
import logging
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import six

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

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
}


def ensure_binary(value):
    if isinstance(value, six.text_type):
        return value.encode(encoding="utf-8")
    return value


def ensure_text(value):
    if isinstance(value, six.binary_type):
        return str(value)
    return value


def requests_retry_session(
        retries=3,
        backoff_factor=0.3,
        status_forcelist=(500, 502, 504),
        session=None,
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        method_whitelist=frozenset(['POST', 'GET']),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def default_value_to_str(x):
    return str(x)


VALUE_TO_STR = {
    type(datetime(year=2018, month=1, day=1)): lambda v: v.strftime('%Y-%m-%d %H:%M:%S'),
    type('a'): lambda v: ensure_text(v),
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

        for k, v in list(dict(self.values, **args).items()):
            kk = k.replace('__', '.')
            if hasattr(v, 'read'):
                files[kk] = v
            elif v is not None:
                data[kk] = VALUE_TO_STR.get(type(v), default_value_to_str)(v)

        args_str = "".join(["{}{}".format(k, data[k]) for k in sorted(data.keys())])
        sign = hmac.new(ensure_binary(self.sec), ensure_binary(args_str), digestmod=hashlib.md5)

        data['sign'] = sign.hexdigest().upper()
        return data, files

    def run(self):
        data, files = self.sign()
        ret = {}
        retry_count = self.client.retry_count

        # prepared data for logging
        method = data.get('method', '')
        input_args = json.dumps(dict(data, **dict([(k, str(v)) for k, v in six.iteritems(files)])), ensure_ascii=False)
        ts_used = 0.0

        def do_log(r):
            output_args = json.dumps(r, ensure_ascii=False)
            log_data = '[TOP_API_CALL] {ts_used:2f}ms |xxx| {method} |xxx| {input_args} |xxx| {output_args}'.format(
                ts_used=ts_used, method=method, input_args=input_args, output_args=output_args)

            if 'error_response' in r:
                logger.warning(log_data)
            elif method.startswith("taobao.ump") or method.startswith("taobao.promotion"):
                logger.info(log_data)
            else:
                logger.debug(log_data)

        for try_id in range(retry_count):
            for f in list(files.values()):
                f.seek(0)

            ts_start = time.time()
            ret = self.open(data, files)
            ts_used = (time.time() - ts_start) * 1000
            do_log(ret)

            if 'error_response' in ret:
                sub_code = ret['error_response'].get('sub_code')
                if sub_code in self.retry_sub_codes:
                    continue
                elif sub_code == 'accesscontrol.limited-by-api-access-count':
                    if try_id < retry_count - 1:
                        ts_sleep = 0.1 * math.pow(2, try_id)
                        logger.warning("meet access-control, sleep %.3lf seconds", ts_sleep)
                        time.sleep(ts_sleep)
                    continue
            break

        if 'error_response' in ret:
            r = ret['error_response']
            raise TaoBaoAPIError(data, **r)

        return ret

    def open(self, data, files):
        raise NotImplementedError("open function should be implemented")


class DefaultAPIRequest(BaseAPIRequest):
    """The Basic API Request"""

    def __init__(self, url, client, values):
        super(DefaultAPIRequest, self).__init__(url, client, values)
        self._session = None

    @property
    def session(self):
        if not self._session:
            self._session = requests_retry_session()
        return self._session

    def open(self, data, files):
        for f in list(files.values()):
            f.seek(0)

        if len(files) == 0:
            timeout = 5
        else:
            timeout = 20

        default_headers = {'Accept-Encoding': 'gzip', 'Connection': 'close'}
        r = self.session.post(self.url, data, files=files, headers=default_headers, timeout=timeout)

        try:
            return r.json()
        except ValueError:
            try:
                text = r.text.replace('\t', '\\t').replace('\n', '\\n').replace('\r', '\\r')
                return json.loads(text)
            except ValueError as e:
                return {
                    "error_response": {"msg": "json decode error", "sub_code": "ism.json-decode-error",
                                       "code": 15, "sub_msg": "json-error: %s || %s" % (str(e), r.text)}}


class TaoBaoAPIError(Exception):
    """raise APIError if got failed json message."""

    def __init__(self, request, code='', msg='', sub_code='', sub_msg='', request_id='', **kwargs):
        """TaoBao SDK Error, Raised From TaoBao"""
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
            code=self.code, msg=self.msg, sub_code=self.sub_code, sub_msg=self.sub_msg,
            request_id=self.request_id, request=self.request)

    def __str__(self):
        """Build String For All the Request and Response"""
        return "{code}|{msg}|{sub_code}|{sub_msg}|{request_id}".format(
            code=self.code, msg=self.msg, sub_code=self.sub_code, sub_msg=self.sub_msg,
            request_id=self.request_id, request=self.request)

    def str2(self):
        """Build String For the Request only"""
        return "{code}|{msg}|{sub_code}|{sub_msg}|{request_id}".format(
            code=self.code, msg=self.msg, sub_code=self.sub_code, sub_msg=self.sub_msg,
            request_id=self.request_id, request=self.request)


class HttpObject(object):
    def __init__(self, client):
        self.client = client

    def __getattr__(self, attr):
        def wrap(**kw):
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

    def __init__(self, app_key, app_secret, domain='gw.api.taobao.com', fetcher_class=DefaultAPIRequest,
                 retry_sub_codes=None, retry_count=5, **kw):
        """Init API Client"""
        self.client_id = app_key
        self.client_secret = app_secret
        self.gw_url = 'http://%s/router/rest' % (domain,)
        self.access_token = None
        self.expires = 0.0
        self.fetcher_class = fetcher_class
        self.get = HttpObject(self)
        self.post = HttpObject(self)
        self.upload = HttpObject(self)
        self.retry_sub_codes = retry_sub_codes if retry_sub_codes else RETRY_SUB_CODES
        self.retry_count = retry_count
        self.kw = kw

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
