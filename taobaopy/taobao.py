#!/usr/bin/env python
# -*- coding: utf-8 -*-
__version__ = '1.1'
__author__ = 'Fred Wang (taobao-pysdk@1e20.com)'

'''
Python client SDK for taobao API.
Many thanks to http://code.google.com/p/sinaweibopy/
'''

import gzip
import json
import time
import urllib
import urllib2
import hashlib
import hmac
import mimetools
import mimetypes
import logging
from datetime import datetime


api_logger = logging.getLogger('taobao_api')
api_error_logger = logging.getLogger('taobao_api_error')

RETRY_SUB_CODES = {
    'isp.top-remote-unknown-error',
    'isp.top-remote-connection-timeout',
    'isp.remote-connection-error',
    'isp.top-remote-service-unavailable',
    'isp.top-remote-connection-timeout-tmall'
}


class TaoBaoAPIError(StandardError):
    """
    raise APIError if got failed json message.
    """

    def __init__(self, request, code, msg, sub_code, sub_msg):
        """
        TaoBao SDK Error, Raised From TaoBao
        """
        self.request = request
        self.code = code
        self.msg = msg
        self.sub_code = sub_code
        self.sub_msg = sub_msg
        StandardError.__init__(self, self.__str__())

    def __str__(self):
        """
        Build String For All the Request and Response
        """
        return "%s|%s|%s|%s|%s" % (str(self.code), self.msg, str(self.sub_code), self.sub_msg, self.request)

    def str2(self):
        """
        Build String For the Request only
        """
        return "%s|%s|%s|%s" % (str(self.code), self.msg, str(self.sub_code), self.sub_msg)


def _get_content_type(filename):
    """
    Get Content Type From File
    """
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'


def _encode_params(**kw):
    """
    Encode parameters.
    """
    return urllib.urlencode(kw)


def _encode_multipart(**kw):
    """
    Encode parameters multipart
    """
    BOUNDARY = mimetools.choose_boundary()
    CRLF = '\r\n'
    L = []
    for (k, v) in kw.iteritems():
        if not hasattr(v, 'read'):
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"' % k)
            L.append('')
            L.append(v)
        else:
            filename = getattr(v, 'name').encode('us-ascii', 'ignore')
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"; \
                    filename="%s"' % (k, filename))
            L.append('Content-Type: %s' % _get_content_type(filename))
            L.append('')
            L.append(v.read())
            v.close()
    L.append('--' + BOUNDARY + '--')
    L.append('')
    body = CRLF.join(L)
    return body, BOUNDARY


_HTTP_GET = 0
_HTTP_POST = 1
_HTTP_UPLOAD = 2


def _http_get(url, authorization=None, **kw):
    """
    Do HTTP Get Request
    """
    logging.info('GET %s' % url)
    return _http_call(url, _HTTP_GET, authorization, **kw)


def _http_post(url, authorization=None, **kw):
    """
    Do HTTP Post Request
    """
    logging.info('POST %s' % url)
    return _http_call(url, _HTTP_POST, authorization, **kw)


def _http_upload(url, authorization=None, **kw):
    """
    Do HTTP MultiPart Post Request
    """
    logging.info('MULTIPART POST %s' % url)
    return _http_call(url, _HTTP_UPLOAD, authorization, **kw)


def _hash_sign(client_secret, **kw):
    """
    Generate Hash Sigh For Request Args
    """
    sign_method = kw['sign_method']
    args_str = "".join(["%s%s" % (k, kw[k]) for k in sorted(kw.keys()) if not isinstance(kw[k], file)])
    if sign_method == 'md5':
        sign = hashlib.md5(client_secret + args_str + client_secret)
        return ('md5', sign.hexdigest().upper())
    else:
        sign = hmac.new(client_secret)
        sign.update(args_str)
        return ('hmac', sign.hexdigest().upper())


def _http_build_req(url, http_method, client, **kw):
    '''
    Do the Request
    '''
    app_key = client.client_id
    app_sec = client.client_secret

    # parse args here
    kww = {}
    for k, v in kw.iteritems():
        if k.find('__'): k = k.replace('__', '.')
        if isinstance(v, file):
            kww[k] = v #File
        elif v: # Not File
            if isinstance(v, datetime):
                kww[k] = v.strftime('%Y-%m-%d %H:%M:%S')
            elif isinstance(v, unicode):
                kww[k] = v.encode('utf-8')
            elif isinstance(v, str):
                kww[k] = v
            elif isinstance(v, float):
                kww[k] = "%.2f" % v
            elif isinstance(v, int):
                kww[k] = str(v)
            else:
                kww[k] = str(v)

    args = {'app_key': app_key, 'sign_method': 'hmac'}
    kww.update(args)
    sign_method, sign = _hash_sign(app_sec, **kww)
    kww['sign'], kww['sign_method'] = sign, sign_method
    boundary = None
    if http_method == _HTTP_UPLOAD:
        params, boundary = _encode_multipart(**kww)
    else:
        params = _encode_params(**kww)
    http_url = '%s?%s' % (url, params) if http_method == _HTTP_GET else url
    http_body = None if http_method == _HTTP_GET else params
    req = urllib2.Request(http_url, data=http_body)
    if boundary:
        req.add_header('Content-Type', 'multipart/form-data; boundary=%s' \
                                       % boundary)
    keys = [k for k, v in kww.items() if not isinstance(v, str)]
    for k in keys: kww[k] = str(kww[k])
    return req, kww


def _http_call_item(cli_, req, kww):
    resp = cli_.fetcher(req)
    start = time.time()
    api_call_time = time.time() - start
    if hasattr(resp, 'read'):
        body = resp.read()
    else:
        body = resp
    if body:
        body = body.replace("\n", "\\n").replace("\t", "\\t")
    else:
        body = '{"error_response":{"msg": "empty body", "sub_code": "mz.emptybody", "code": 301, "sub_msg": "empty http response body"}}'
    #    body here
    sign_args = "%.6fms" % (api_call_time * 1000)
    req_args = json.dumps(kww, ensure_ascii=False)
    resp_args = body
    log_data = '%s [{>.<}] %s [{>.<}] %s' % (sign_args, req_args, resp_args)

    api_logger.debug(log_data)
    try:
        r = json.loads(body)
    except ValueError, e:
        r = {u'error_response': {u'msg': u'json decode error', u'sub_code': u'mz.json_error', u'code': 301,
                                 u'sub_msg': str(e)}}
    if not r or 'error_response' in r:
        api_error_logger.warn(log_data)
        if r:
            r2 = r['error_response']
            raise TaoBaoAPIError(req_args, r2.get('code'), r2.get('msg'), r2.get('sub_code'), r2.get('sub_msg'))
        else:
            raise TaoBaoAPIError(req_args, '0', 'json format error', '0', '0')
    return r


def _http_call(url, http_method, client, **kw):
    """
    Do HTTP Request with 3 tries
    """
    req, kww = _http_build_req(url, http_method, client, **kw)
    for tries in xrange(3, -1, -1):
        try:
            r = _http_call_item(client, req, kww)
            return r
        except TaoBaoAPIError, e:
            if tries == 0: raise
            if e.sub_code in RETRY_SUB_CODES: continue
            raise


class HttpObject(object):
    def __init__(self, client, http_method):
        self.client = client
        self.http_method = http_method

    def __getattr__(self, attr):
        def wrap(**kw):
            method = "taobao." + attr.replace('_', '.')
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if self.client.is_expires() or 'session' in kw:
                return _http_call(self.client.gw_url, self.http_method,
                                  self.client, method=method, timestamp=timestamp,
                                  format='json', v='2.0', **kw)
            else:
                return _http_call(self.client.gw_url, self.http_method,
                                  self.client, session=self.client.access_token, v='2.0',
                                  timestamp=timestamp, format='json', method=method, **kw)

        return wrap


def _default_fetcher(request, debug=0):
    for i in xrange(3):
        try:
            r = urllib2.urlopen(request, timeout=5)
            data = r.read()
            return data
        except:
            pass
    return


try:
    import pycurl
    from StringIO import StringIO

    def _pycurl_fetcher(req, debug=False):
        """
        pycurl fetcher without debug
        """
        b = StringIO()
        h = StringIO()
        url = req.get_full_url()
        c = pycurl.Curl()
        c.setopt(pycurl.URL, url)
        c.setopt(pycurl.WRITEFUNCTION, b.write)
        c.setopt(pycurl.HEADERFUNCTION, h.write)
        c.setopt(pycurl.FOLLOWLOCATION, 1)
        c.setopt(pycurl.MAXREDIRS, 5)
        if req.get_method() == 'POST':
            c.setopt(pycurl.POSTFIELDS, req.get_data())
            c.setopt(pycurl.POST, 1)
        headers = [": ".join(x) for x in req.header_items()]
        headers.append('Accept-Encoding: gzip')
        c.setopt(pycurl.HTTPHEADER, headers)

        if debug:
            c.setopt(pycurl.VERBOSE, 1)
        c.perform()
        # parse headers
        headers = dict([tuple(x.split(': ')[:2]) for x in h.getvalue().split('\r\n') if x and x.find(':') > 0])
        if headers.get('Content-Encoding') == 'gzip':
            f = gzip.GzipFile(fileobj=StringIO(b.getvalue()))
            return f.read()
        return b.getvalue()

except ImportError:
    _pycurl_fetcher = _default_fetcher


class TaoBaoAPIClient(object):
    """
    API client using synchronized invocation.
    """
    def __init__(self, app_key, app_secret, fetcher=_pycurl_fetcher, \
                 sign_method='hmac', domain='gw.api.taobao.com'):
        self.client_id = app_key
        self.client_secret = app_secret
        self.sign_method = sign_method
        self.gw_url = 'http://%s/router/rest' % (domain,)
        self.access_token = None
        self.expires = 0.0
        self.fetcher = fetcher
        self.get = HttpObject(self, _HTTP_GET)
        self.post = HttpObject(self, _HTTP_POST)
        self.upload = HttpObject(self, _HTTP_UPLOAD)

    def set_access_token(self, access_token, expires_in=2147483647):
        self.access_token = str(access_token)
        self.expires = float(expires_in)

    def set_fetcher(self, fetcher):
        self.fetcher = fetcher

    def is_expires(self):
        return not self.access_token or time.time() > self.expires

    def __getattr__(self, attr):
        return getattr(self.post, attr)


class APIClient(TaoBaoAPIClient):
    pass


class APIError(TaoBaoAPIError):
    pass
