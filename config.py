# These values can be overridden in config_local.py
ORDERS_DIR = './orders'
REPORT_URL = ''
TIME_ZONE = 'US/Central'
GDRIVE_FOLDER = 'Shipping Label Inbox'

from pathlib import Path
from config_local import *


ebay_keys = ('appid', 'devid', 'certid', 'token')
EBAY_CREDENTIALS = EBAY_PARAMS


BACKUP_PATH = Path(__file__).parent.parent / 'ebay-backup/items'
