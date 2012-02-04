from taobao import *

def _debug_fetcher(request,debug=True):
    "A debug fetcher for urllib2"
    if debug:
        level = 1
    else:
        level = 0    
    opener = urllib2.build_opener(urllib2.HTTPHandler(debuglevel=level))
    return opener.open(request,timeout=5)

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
    _pycurl_fetcher = _debug_fetcher

def _pycurl_debug(req):
    "pycurl fetcher with debug"
    return _pycurl_fetcher(req,debug=True)
        
def test():
    key = 'Your API KEY HERE'
    sec = 'Your API SECRET HERE'
    token = 'Your Session Key HERE'

    # build APIClient with default fetcher 
    client = APIClient(key,sec)#,fetcher=_my_fetcher)
    # use pycurl fetcher
#    client = APIClient(key,sec,fetcher=_pycurl_fetcher)
    print client.post.items_get(nicks='kamozi',fields='num_iid,title,price',page_no=1,page_size=2)
    
    print client.user_get(fields='nick,uid,user_id,email',session=token)

#    return
    NUM_IID = 'Your Numiid HERE'
    client.set_fetcher(_pycurl_debug)
    print client.upload.item_img_upload(num_iid=NUM_IID,is_major='true',image=open("logo.png","rb"),session=token)

    client.set_fetcher(_pycurl_fetcher)
    client.set_access_token(token)
    print client.upload.item_img_upload(num_iid=NUM_IID,is_major='true',image=open("logo.png","rb"))

if __name__ == '__main__':
    test()
 
