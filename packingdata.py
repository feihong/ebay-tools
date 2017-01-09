import subprocess
import re
import collections
import json
from pathlib import Path

from PyPDF2 import PdfFileReader
import attr

import config
from orders import download_shipped_orders


@attr.s
class TrackingNumberMeta:
    slug = attr.ib(default='')
    # Area on label where tracking number is found.
    bbox = attr.ib(default=())
    # Where to write packing data and how to rotate the text.
    output_params = attr.ib(default={})

    def __str__(self):
        return '<{}>'.format(slug)


DOMESTIC_TOP = TrackingNumberMeta(
    slug='domestic-top',
    bbox=(140, 95, 30, 195),
    output_params=dict(translate=(411, 325), rotate=180),
)
DOMESTIC_BOTTOM = TrackingNumberMeta(
    slug='domestic-bottom',
    bbox=(140, 495, 30, 195),
    output_params=dict(translate=(411, 722), rotate=180),
)
FOREIGN = TrackingNumberMeta(
    slug='foreign',
    bbox=(265, 275, 250, 100),
    output_params=dict(translate=(537, 143), rotate=-90),
)


@attr.s
class TrackingNumber:
    meta = attr.ib()
    value = attr.ib(default='')


def add_packing_data(pdf_file):
    json_file = 'shipped_orders.json'
    # download_shipped_orders(json_file)
    tn_map = get_tracking_number_map(json_file)
    print(tn_map)

    reader = PdfFileReader(open(pdf_file, 'rb'))

    for page_index in range(0, reader.numPages):
        print(get_tracking_numbers(pdf_file, page_index))


def get_tracking_number_map(json_file):
    """
    Return a dict where the keys are tracking numbers and the values are lists
    of items (in a order).

    """
    result = collections.defaultdict(list)

    orders_file = Path(config.ORDERS_DIR) / json_file
    orders = json.load(orders_file.open())
    for order in orders:
        for tnum in get_tracking_numbers_for_order(order):
            result[tnum].extend(order['items'])

    return result


def get_tracking_numbers_for_order(order):
    tracking_nums = []
    transactions = order['TransactionArray']['Transaction']
    for transaction in transactions:
        try:
            details = transaction['ShippingDetails']['ShipmentTrackingDetails']
        except KeyError:
            details = []

        if not isinstance(details, list):
            details = [details]

        for detail in details:
            tn = detail['ShipmentTrackingNumber']
            tracking_nums.append(tn)

    return tracking_nums


def get_tracking_numbers(pdf_file, page_index):
    result = []

    for tn_meta in (DOMESTIC_TOP, DOMESTIC_BOTTOM):
        text = get_text_for_bbox(pdf_file, page_index, tn_meta.bbox)
        # Must be 22-digit number.
        if re.match(r'\d{22}', text):
            tn = TrackingNumber(meta=tn_meta, value=text)
            result.append(tn)

    text = get_text_for_bbox(pdf_file, page_index, FOREIGN.bbox)
    # Must be two letters, then 9 digits, then 'US'.
    if re.match(r'[A-Z]{2}\d{9}US', text):
        tn = TrackingNumber(meta=FOREIGN, value=text)
        result.append(tn)

    return result


def get_text_for_bbox(pdf_file, page_index, bbox):
    x, y, w, h = (str(num) for num in bbox)
    page_num = str(page_index + 1)

    cmd = [
        'pdftotext',
        pdf_file,
        '-f', page_num,    # first page
        '-l', page_num,    # last page
        # Crop parameters
        '-x', x,
        '-y', y,
        '-W', w,
        '-H', h,
        # Send output to stdout
        '-'
    ]
    result = subprocess.check_output(cmd)
    result = result.decode('utf-8')
    return result.strip().replace(' ', '')      # get rid of all extraneous spaces
