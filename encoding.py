import sys
if sys.version_info < (3, 0):
    reload(sys)  # noqa: F821
    sys.setdefaultencoding("utf-8")
