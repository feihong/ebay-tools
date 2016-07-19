import os

EBAY_PARAMS = os.environ['EBAY_PARAMS']
SMS_NUMBER = os.environ['SMS_NUMBER']
REPORT_PATH = 'report.html'
REPORT_URL = None

credentials = dict(zip(
    ('appid', 'devid', 'certid', 'token'), EBAY_PARAMS.split(';')))
