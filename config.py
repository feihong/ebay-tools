import os

EBAY_PARAMS = os.environ['EBAY_PARAMS']

credentials = dict(zip(
    ('appid', 'devid', 'certid', 'token'), EBAY_PARAMS.split(';')))
