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
        StandardError.__init__(self, msg)

    def __str__(self):
        return "%s|%s|%s|%s"%(str(self.code),self.msg,str(self.sub_code),self.sub_msg)


def _get_content_type(filename):
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'


def _encode_params(**kw):
    '''
    Encode parameters.
    '''
    args = []
    for k, v in kw.iteritems():
        qv = v.encode('utf-8') if isinstance(v, unicode) else str(v)
        args.append('%s=%s' % (k, urllib.quote(qv)))
    return '&'.join(args)


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


def _hash_sign(client_id, client_secret, sign_method='md5', **kw):
    args = {'app_key': client_id, 'sign_method': sign_method}
    for k, v in kw.items():
        if hasattr(v, 'read'):
            continue
        args[k] = v.encode('utf-8') if isinstance(v, unicode) else str(v)
    args_str = "".join(["%s%s" % (k, args[k]) for k in sorted(args.keys())])
    if sign_method == 'md5':
        sign = hashlib.md5(client_secret + args_str + client_secret)
        return ('md5', sign.hexdigest().upper())
    else:
        sign = hmac.new(client_secret)
        sign.update(args_str)
        return ('hmac', sign.hexdigest().upper())


def _http_call(url, http_method, client, **kw):
    '''
    Do the Request
    '''
    app_key = client.client_id
    app_sec = client.client_secret
    sign_method, sign = _hash_sign(app_key, app_sec, sign_method='hmac', **kw)
    params = None
    boundary = None
    if http_method == _HTTP_UPLOAD:
        params, boundary = _encode_multipart(app_key=app_key,\
            sign=sign, sign_method=sign_method, **kw)
    else:
        params = _encode_params(app_key=app_key, sign=sign,\
            sign_method=sign_method, **kw)
    http_url = '%s?%s' % (url, params) if http_method == _HTTP_GET else url
    http_body = None if http_method == _HTTP_GET else params
    req = urllib2.Request(http_url, data=http_body)
    if boundary:
        req.add_header('Content-Type', 'multipart/form-data; boundary=%s'\
        % boundary)
    resp = client.fetcher(req)
    if hasattr(resp, 'read'):
        body = resp.read()
    else:
        body = resp
    body = body.replace("\n","\\n").replace("\t","\\t")
#    body here
    sign_args = "|".join((app_key,sign,sign_method))
    req_args = json.dumps(kw,ensure_ascii=False)
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


def _default_fetcher(request):
    for i in xrange(3):
        try:
            r = urllib2.urlopen(request, timeout=5)
            data = r.read()
            return data
        except:
            pass
    return


class APIClient(object):
    '''
    API client using synchronized invocation.
    '''

    def __init__(self, app_key, app_secret, fetcher=_default_fetcher,\
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
