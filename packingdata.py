import collections

import attr
from PyPDF2 import PdfFileReader

import config
from orders import download_shipped_orders, load_orders


@attr.s
class TrackingNumberMeta:
    # One of: domestic-top, domestic-bottom, foreign
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
    output_params=dict(translate=(411, 325), rotate=180, chars=39, lines=3),
)
DOMESTIC_BOTTOM = TrackingNumberMeta(
    slug='domestic-bottom',
    bbox=(140, 495, 30, 195),
    output_params=dict(translate=(411, 722), rotate=180, chars=39, lines=3),
)
FOREIGN = TrackingNumberMeta(
    slug='foreign',
    bbox=(265, 275, 250, 100),
    output_params=dict(translate=(537, 143), rotate=-90, chars=29, lines=6),
)


@attr.s(repr=False)
class TrackingNumber:
    meta = attr.ib(default=None)
    value = attr.ib(default='')

    def __repr__(self):
        return '{} ({})'.format(self.value, self.meta.slug)


@attr.s
class OutputInfo:
    params = attr.ib(default={})
    value = attr.ib(default='')

    @property
    def wrapped_text(self):
        "Return text wrapped according to the output parameters."
        import textwrap
        result = textwrap.fill(self.text, self.output_params['chars'])
        line_count = len(result.splitlines())
        assert line_count <= self.output_params['lines']
        return result


class PackingInfoAdder:
    def __init__(self, pdf_file):
        self.pdf_file = pdf_file
        self.reader = PdfFileReader(open(pdf_file, 'rb'))
        self.tn_pi = self.build_tracking_number_packing_info_map()

    def get_packing_info_list(self):
        result = []

        for tracking_numbers in self.get_tracking_numbers_from_pdf(self):
            packing_infos = [self.tn_pi.get(tn, '') for tn in tracking_numbers]
            result.append(packing_infos)

        return result

    def get_tracking_numbers_from_pdf(self):
        for page_index in range(0, self.reader.numPages):
            yield get_tracking_numbers_from_page(self.pdf_file, page_index)

    def get_shipped_orders(self):
        for user, orders in load_orders('shipped_orders.json')['payload'].items():
            for order in orders:
                yield order

    def build_tracking_number_packing_info_map(self):
        result = collections.defaultdict(list)

        for order in self.get_shipped_orders():
            for tn in get_tracking_numbers_for_order(order):
                result[tn].append(order['packing_info'])

        # Join the lists into strings.
        return dict((k, ', '.join(v)) for k, v  in result.items())


def get_tracking_number_map(json_file):
    """
    Return a dict where the keys are tracking numbers and the values are lists
    of packing_info strings.

    """
    result = collections.defaultdict(list)

    for user, orders in load_orders(json_file):
        for order in orders:
            for tnum in get_tracking_numbers_for_order(order):
                result[tnum].append(order['packing_info'])

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


def get_tracking_numbers_from_page(pdf_file, page_index):
    """
    Return a list of tracking numbers for the given page of the given pdf file.
    """
    import re

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
