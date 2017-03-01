import collections
import textwrap
import json

import attr
from PyPDF2 import PdfFileReader

import config
from orders import download_shipped_orders, load_orders


@attr.s
class TrackingNumberReadMeta:
    """
    This class stores the bounding box for a particular type of tracking number.

    """
    entries = {}

    # One of: domestic-top, domestic-bottom, foreign
    type = attr.ib(default='')
    # Area on label where tracking number is found.
    bbox = attr.ib(default=())

    @classmethod
    def add_meta(cls, type, bbox):
        cls.entries[type] = TrackingNumberReadMeta(type=type, bbox=bbox)

    @classmethod
    def get(cls, type):
        return cls.entries[type]


TrackingNumberReadMeta.add_meta(
    type='domestic-top',
    bbox=(140, 95, 30, 195),
)
TrackingNumberReadMeta.add_meta(
    type='domestic-bottom',
    bbox=(140, 495, 30, 195),
)
TrackingNumberReadMeta.add_meta(
    type='foreign',
    bbox=(265, 275, 250, 100),
)


@attr.s
class ShippingLabelOutputMeta:
    """
    This class stores the output parameters for a particular type of shipping
    label output.

    """
    entries = {}

    type = attr.ib(default='')      # type of tracking number
    translate = attr.ib(default=(10, 10))
    rotate = attr.ib(default=0)
    max_len = attr.ib(default=20)
    max_lines = attr.ib(default=2)

    @classmethod
    def add_meta(cls, type, **kwargs):
        cls.entries[type] = ShippingLabelOutputMeta(type=type, **kwargs)

    @staticmethod
    def get_output_info(type, text):
        attrname = type.upper().replace('-', '_')
        meta = getattr(TrackingNumberOutputMeta, attrname)
        text = textwrap.fill(text, meta.max_len)
        return OutputInfo(
            text=text,
            overflow=len(text.splitlines()) > meta.max_lines,
            translate=meta.translate,
            rotate=meta.rotate,
        )


ShippingLabelOutputMeta.add_meta(
    type='domestic-top',
    translate=(244, 316),
    rotate=0,
    max_len=32,
    max_lines=2,
)
ShippingLabelOutputMeta.add_meta(
    type='domestic-bottom',
    translate=(244, 713),
    rotate=0,
    max_len=32,
    max_lines=2,
)
ShippingLabelOutputMeta.add_meta(
    type='foreign',
    translate=(537, 143),
    rotate=-90,
    max_len=23,
    max_lines=5,
)


@attr.s(repr=False)
class TrackingNumber:
    type = attr.ib(default='domestic-top')
    value = attr.ib(default='0000 0000 0000 0000')

    def __repr__(self):
        return '{} ({})'.format(self.value, self.type)

    def __hash__(self):
        return hash(self.value)


@attr.s(repr=False)
class OutputInfo:
    text = attr.ib(default='xxx xxx')
    overflow = attr.ib(default=False)       # if text takes up too many lines
    translate = attr.ib(default=(10, 10))
    rotate = attr.ib(default=0)

    def __repr__(self):
        return '{} ({})'.format(self.text, self.overflow)


class PackingInfoAdder:
    def __init__(self, pdf_file):
        self.pdf_file = pdf_file
        self.reader = PdfFileReader(open(pdf_file, 'rb'))
        self.tn_pi = self.build_tracking_number_packing_info_map()

    def get_output_infos(self):
        result = []

        for tracking_numbers in self.get_tracking_numbers_from_pdf(self):
            output_infos = [self.get_output_info(tn) for tn in tracking_numbers]
            result.append(output_infos)

        return result

    def get_output_info(self, tracking_num):
        meta = OutputInfoMeta.get(tracking_num.key)
        packing_info = self.tn_pi.get(tracking_num, '')
        return OutputInfo(meta=meta, value=packing_info)

    def get_tracking_numbers_from_pdf(self):
        for page_index in range(0, self.reader.numPages):
            yield get_tracking_numbers_from_page(self.pdf_file, page_index)


def get_shipped_orders():
    for user, orders in load_orders('shipped_orders.json')['payload'].items():
        for order in orders:
            yield order


def generate_tracking_num_to_order_id_file():
    output_file = 'orders/tracking_num_to_order_id.json'
    result = collections.defaultdict(list)

    for order in get_shipped_orders():
        for tn in get_tracking_numbers_for_order(order):
            result[tn].append(order['OrderID'])

    print('Found {} tracking numbers'.format(len(result)))
    with open(output_file, 'w') as fp:
        json.dump(result, fp, indent=2)


# def get_tracking_number_map(json_file):
#     """
#     Return a dict where the keys are tracking numbers and the values are lists
#     of packing_info strings.
#
#     """
#     result = collections.defaultdict(list)
#
#     for user, orders in load_orders(json_file):
#         for order in orders:
#             for tnum in get_tracking_numbers_for_order(order):
#                 result[tnum].append(order['packing_info'])
#
#     return result

def generate_tracking_num_to_packing_info_file():
    output_file = 'orders/tracking_num_to_packing_info.json'

    # Get order dict keyed by OrderID.
    orders = dict((o['OrderID'], o) for o in get_shipped_orders())

    result = json.load(open('orders/tracking_num_to_order_id.json'))
    keys = result.keys()
    for tracking_num in keys:
        order_ids = result[tracking_num]
        packing_info = '; '.join(orders[id]['packing_info'] for id in order_ids)
        result[tracking_num] = packing_info

    with open(output_file, 'w') as fp:
        json.dump(result, fp, indent=2)




def get_tracking_numbers_for_order(order):
    tracking_nums = set()

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
            tracking_nums.add(tn)

    return tracking_nums


def get_tracking_numbers_from_page(pdf_file, page_index):
    """
    Return a list of tracking numbers for the given page of the given pdf file.

    """
    import re

    result = []

    for type in ('domestic-top', 'domestic-bottom'):
        bbox = TrackingNumberReadMeta.get(type).bbox
        text = get_text_for_bbox(pdf_file, page_index, bbox)
        # Must be 22-digit number.
        if re.match(r'\d{22}', text):
            tn = TrackingNumber(type=type, value=text)
            result.append(tn)

    foreign = TrackingNumberReadMeta.get('foreign')
    text = get_text_for_bbox(pdf_file, page_index, foreign.bbox)
    # Must be two letters, then 9 digits, then 'US'.
    if re.match(r'[A-Z]{2}\d{9}US', text):
        tn = TrackingNumber(type='foreign', value=text)
        result.append(tn)

    return result


def get_text_for_bbox(pdf_file, page_index, bbox):
    """
    For the given PDF file, return all the text on page `page_index` inside
    bounding box `bbox`.

    """
    import subprocess

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
