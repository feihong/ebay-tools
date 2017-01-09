import subprocess
import re
import collections

from PyPDF2 import PdfFileReader
import attr

import config
import orders


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
    # tn_map = get_tracking_number_map()
    # print(tn_map)

    reader = PdfFileReader(open(pdf_file, 'rb'))

    for page_index in range(0, reader.numPages):
        print(get_tracking_numbers(pdf_file, page_index))


def get_tracking_number_map():
    """
    Return a dict where the keys are tracking numbers and the values are lists
    of items (in a order).

    """
    result = collections.defaultdict([])

    for user_id, cred in config.EBAY_CREDENTIALS:
        request = OrderRequest(cred)
        orders = request.get_shipped_orders()
        for order in orders:
            tnum = get_tracking_number(order)
            items = request.get_items(order)
            result[tnum].extend(items)

    return result


def get_tracking_number(order):
    tracking_nums = []
    transactions = order['TransactionArray']['Transaction']
    for transaction in transactions:
        try:
            tn = (transaction['ShippingDetails']['ShipmentTrackingDetails']
                ['ShipmentTrackingNumber'])
            tracking_nums.append(tn)
        except KeyError:
            pass

    if len(tracking_nums) == 0:
        return None

    # Make sure that all tracking nums are the same.
    assert all(n == tracking_nums[0] for n in tracking_nums)
    return tracking_nums[0]


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
