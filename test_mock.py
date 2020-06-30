import requests_mock
from taobaopy.taobao import TaoBaoAPIClient, TaoBaoAPIError
from io import BytesIO


class NamedBytesIO(BytesIO):
    def __init__(self, content, name):
        self.name = name
        self.length = len(content)
        super(NamedBytesIO, self).__init__(content)


def test_no_json():
    with requests_mock.mock() as m:
        m.post("http://test.com/router/rest", text='not json')
        c = TaoBaoAPIClient(app_key="key", app_secret="sec", domain="test.com", retry_count=1)
        try:
            c.time_get()
            assert False
        except TaoBaoAPIError as e:
            if e.sub_code != "ism.json-decode-error":
                assert False
        except Exception:
            assert False


def test_normal():
    with requests_mock.mock() as m:
        m.post("http://test.com/router/rest", text='{"time_get_response":{"time":"2000-01-01 00:00:00"}}')
        c = TaoBaoAPIClient(app_key="key", app_secret="sec", domain="test.com", retry_count=1)
        res = c.time_get()
        assert res["time_get_response"]["time"] == '2000-01-01 00:00:00'


def test_json_fix():
    with requests_mock.mock() as m:
        m.post("http://test.com/router/rest", text='''{"time_get_response":{"time":"\n\r\t2000-01-01 00:00:00"}}''')
        c = TaoBaoAPIClient(app_key="key", app_secret="sec", domain="test.com", retry_count=1)
        res = c.time_get(a=123)
        assert res["time_get_response"]["time"] == '\n\r\t2000-01-01 00:00:00'


def test_upload():
    with requests_mock.Mocker() as m:
        m.post("http://test.com/router/rest", text='{}')
        c = TaoBaoAPIClient(app_key="key", app_secret="sec", domain="http://test.com", retry_count=1)
        res = c.time_get(file1=NamedBytesIO(b"abc", "test.png"))
        assert res == {}
