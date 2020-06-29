from .taobao import attr_to_method, get_gw_url


def test_attr_to_method():
    data = (("item_get", "taobao.item.get"), ("time_get", "taobao.time.get"), ("tmall__item_get", "tmall.item.get"), ("taobao__item_get", "taobao.item.get"))
    for i, o in data:
        o2 = attr_to_method(i)
        assert o == o2


def test_get_gw_url():
    data = (
        ("aaa.com", "http://aaa.com/router/rest"),
        ("aaa.com/", "http://aaa.com/router/rest"),
        ("http://aaa.com", "http://aaa.com/router/rest"),
        ("https://aaa.com", "https://aaa.com/router/rest"),
        ("https://aaa.com/", "https://aaa.com/router/rest"),
        ("https://eco.taobao.com/", "https://eco.taobao.com/router/rest"),
        ("https://user:pass@eco.taobao.com/", "https://user:pass@eco.taobao.com/router/rest"),
        ("user:pass@eco.taobao.com/", "http://user:pass@eco.taobao.com/router/rest"),
    )
    for i, o in data:
        assert o == get_gw_url(i)
