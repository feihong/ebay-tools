import os


environ = os.environ


if 'EBAY_PARAMS' in environ:
    EBAY_PARAMS = os.environ['EBAY_PARAMS']
    SMS_NUMBER = os.environ['SMS_NUMBER']
    REPORT_PATH = 'report.html'
    REPORT_URL = ''
else:
    from file_config import *


credentials = dict(zip(
    ('appid', 'devid', 'certid', 'token'), EBAY_PARAMS.split(';')))
