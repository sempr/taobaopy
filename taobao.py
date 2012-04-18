#!/usr/bin/env python
# -*- coding: utf-8 -*-

__version__ = '1.00'
__author__ = 'Fred Wang (i#1e20.com)'

'''
Python client SDK for taobao API.
Many thanks to http://code.google.com/p/sinaweibopy/
'''

import json
import time
import urllib
import urllib2
import hashlib
import hmac
import mimetools
import mimetypes
from datetime import datetime

import logging
import logging.config
try:
    logging.config.fileConfig('logging.ini')
    api_logger = logging.getLogger('api')
    api_error_logger = logging.getLogger('eapi')
except :
    ch = logging.StreamHandler()
    logger = logging.getLogger()
    logger.addHandler(ch)
    api_logger = api_error_logger = logger

class APIError(StandardError):
    '''
    raise APIError if got failed json message.
    '''

    def __init__(self, request, code, msg, sub_code, sub_msg):
        self.request = request

        self.code = code
        self.msg = msg
        self.sub_code = sub_code
        self.sub_msg = sub_msg
        StandardError.__init__(self, self.__str__())

    def __str__(self):
        return "%s|%s|%s|%s|%s"%(str(self.code),self.msg,str(self.sub_code),self.sub_msg,self.request)


def _get_content_type(filename):
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'


def _encode_params(**kw):
    '''
    Encode parameters.
    '''
    return urllib.urlencode(kw)


def _encode_multipart(**kw):
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
            filename = getattr(v, 'name')
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
    logging.info('GET %s' % url)
    return _http_call(url, _HTTP_GET, authorization, **kw)


def _http_post(url, authorization=None, **kw):
    logging.info('POST %s' % url)
    return _http_call(url, _HTTP_POST, authorization, **kw)


def _http_upload(url, authorization=None, **kw):
    logging.info('MULTIPART POST %s' % url)
    return _http_call(url, _HTTP_UPLOAD, authorization, **kw)


def _hash_sign(client_secret, **kw):
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
    for k,v in kw.iteritems():
        if k.find('__'): k = k.replace('__','.')
        if isinstance(v, file):
            kww[k] = v #File
        else: # Not File
            if isinstance(v,datetime):
                kww[k] = v.strftime('%Y-%m-%d %H:%M:%S')
            elif isinstance(v,unicode):
                kww[k] = v.encode('utf-8')
            elif isinstance(v,str):
                kww[k] = v
            elif isinstance(v,float):
                kww[k] = "%.2f"%v
            elif isinstance(v,int):
                kww[k] = str(v)
            else:
                kww[k] = str(v)

    args = {'app_key': app_key, 'sign_method': 'hmac'}
    kww.update(args)
    sign_method, sign = _hash_sign(app_sec, **kww)
    kww['sign'],kww['sign_method'] = sign, sign_method
    boundary = None
    if http_method == _HTTP_UPLOAD:
        params, boundary = _encode_multipart(**kww)
    else:
        params = _encode_params(**kww)
    http_url = '%s?%s' % (url, params) if http_method == _HTTP_GET else url
    http_body = None if http_method == _HTTP_GET else params
    req = urllib2.Request(http_url, data=http_body)
    if boundary:
        req.add_header('Content-Type', 'multipart/form-data; boundary=%s'\
        % boundary)
    keys = [k for k,v in kww.items() if not isinstance(v, str)]
    for k in keys: kww[k] = str(kww[k])
    return req,kww

def _http_call(url, http_method, client, **kw):
    req,kww = _http_build_req(url,http_method,client,**kw)
    start = time.time()
    resp = client.fetcher(req)
    api_call_time = time.time() - start
    if hasattr(resp, 'read'):
        body = resp.read()
    else:
        body = resp
    body = body.replace("\n","\\n").replace("\t","\\t")
#    body here
    sign_args = "%.6fms"%(api_call_time*1000)
    req_args = json.dumps(kww,ensure_ascii=False)
    resp_args = body
    log_data = '%s [{>.<}] %s [{>.<}] %s'%(sign_args, req_args, resp_args)

    api_logger.info(log_data)
    r = json.loads(body)
    if 'error_response' in r:
        r2 = r['error_response']
        api_error_logger.warn(log_data)
        raise APIError(req_args, r2.get('code'), r2.get('msg'), r2.get('sub_code'), r2.get('sub_msg'))
    return r


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
    import StringIO
    def _pycurl_fetcher(req,debug=False):
        "pycurl fetcher without debug"
        b = StringIO.StringIO()
        url = req.get_full_url()
        c = pycurl.Curl()
        c.setopt(pycurl.URL, url)
        c.setopt(pycurl.WRITEFUNCTION, b.write)
        c.setopt(pycurl.FOLLOWLOCATION, 1)
        c.setopt(pycurl.MAXREDIRS, 5)
        if req.get_method() == 'POST':
            c.setopt(pycurl.POSTFIELDS, req.get_data())
            c.setopt(pycurl.POST, 1)
        if req.has_header('Content-type'):
            c.setopt(pycurl.HTTPHEADER, [": ".join(x) for x in req.header_items()])
        if debug:
            c.setopt(pycurl.VERBOSE, 1)
        c.perform()
        return b.getvalue()

except ImportError:
    _pycurl_fetcher = _default_fetcher

class APIClient(object):
    '''
    API client using synchronized invocation.
    '''

    def __init__(self, app_key, app_secret, fetcher=_pycurl_fetcher,\
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
        return getattr(self.get, attr)
