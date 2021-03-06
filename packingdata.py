import collections
import textwrap
import json
import io

import attr
from reportlab.pdfgen.canvas import Canvas
from PyPDF2 import PdfFileReader, PdfFileWriter
from PyPDF2.pdf import PageObject

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

    @classmethod
    def get(cls, type):
        return cls.entries[type]

    @staticmethod
    def get_output_info(type, text):
        meta = ShippingLabelOutputMeta.get(type)
        if meta.max_len is not None:
            text = textwrap.fill(text, meta.max_len)

        if meta.max_lines is not None:
            overflow = len(text.splitlines()) > meta.max_lines
        else:
            overflow = False

        return OutputInfo(
            text=text,
            overflow=overflow,
            translate=meta.translate,
            rotate=meta.rotate,
        )

    @classmethod
    def get_center_line(cls):
        return cls.get_output_info('domestic-center-line', '-  ' * 30)

    @classmethod
    def get_page_number(cls, num, total, label_count):
        return cls.get_output_info(
            'page-number',
            'Page {} of {} ({} labels)'.format(num, total, label_count))

    @classmethod
    def get_username(cls, text):
        return cls.get_output_info('username', 'User: {}'.format(text))


ShippingLabelOutputMeta.add_meta(
    type='domestic-top',
    translate=(244, 316),
    rotate=0,
    max_len=27,
    max_lines=2,
)
ShippingLabelOutputMeta.add_meta(
    type='domestic-bottom',
    translate=(244, 713),
    rotate=0,
    max_len=27,
    max_lines=2,
)
ShippingLabelOutputMeta.add_meta(
    type='domestic-center-line',
    translate=(45, 397),
    rotate=0,
    max_len=None,
    max_lines=None,
)
ShippingLabelOutputMeta.add_meta(
    type='foreign',
    translate=(537, 143),
    rotate=-90,
    max_len=23,
    max_lines=5,
)
ShippingLabelOutputMeta.add_meta(
    type='username',
    translate=(45, 767),
    rotate=0,
    max_len=50,
    max_lines=1,
)
ShippingLabelOutputMeta.add_meta(
    type='page-number',
    translate=(430, 767),
    rotate=0,
    max_len=30,
    max_lines=1,
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
        return '{} {}'.format(self.text, self.translate)


class PackingInfoAdder:
    def __init__(self, pdf_files, label_count=None):
        self.pdf_files = pdf_files
        self._set_input_pages()
        self.label_count = label_count
        with open('orders/tracking_num_to_packing_info.json') as fp:
            self.tn_pi = json.load(fp)

    def write_output_file(self, output_file):
        writer = PdfFileWriter()
        output_pages = self.get_output_pages()

        for input_page, output_page in zip(self.input_pages, output_pages):
            input_page.mergePage(output_page)
            writer.addPage(input_page)
        with output_file.open('wb') as fp:
            writer.write(fp)

    def get_output_pages(self):
        for infos in self.get_output_infos():
            yield self._get_output_page(infos)

    def get_output_infos(self):
        result = []

        tracking_num_collection = list(self.get_tracking_numbers_from_pdfs())
        page_count = len(tracking_num_collection)
        label_count = self.label_count
        if label_count is None:
            label_count = sum(len(lst) for lst in tracking_num_collection)

        for i, tracking_numbers in enumerate(tracking_num_collection, 1):
            output_infos = [self._get_packing_info(tn)
                for tn in tracking_numbers]

            if len(tracking_numbers) != 0:
                # Probably an irregular foreign shipping label (e.g. > 4 lbs).
                output_infos.append(self._get_username(tracking_numbers[0]))

            output_infos.append(
                ShippingLabelOutputMeta.get_page_number(
                    i, page_count, label_count))

            if len(tracking_numbers) >= 2:
                output_infos.append(ShippingLabelOutputMeta.get_center_line())

            result.append(output_infos)

        return result

    def get_tracking_numbers_from_pdfs(self):
        for page_count, pdf_file in zip(self.page_counts, self.pdf_files):
            for i in range(page_count):
                yield get_tracking_numbers_from_page(pdf_file, i)

    def _set_input_pages(self):
        self.input_pages = []
        self.page_counts = []

        for pdf_file in self.pdf_files:
            # EBay label PDFs are a bit weird, so set strict to False.
            reader = PdfFileReader(pdf_file.open('rb'), strict=False)
            self.page_counts.append(reader.numPages)
            for page_index in range(0, reader.numPages):
                page = reader.getPage(page_index)
                height = page.mediaBox[3]
                if height == (5.5 * 72):
                    # This is a half-size page, so make it full size.
                    page2 = get_blank_page()
                    page2.mergeTranslatedPage(page, tx=0, ty=5.5*72)
                    page = page2
                self.input_pages.append(page)

    def _get_packing_info(self, tracking_num):
        order_info = self.tn_pi.get(tracking_num.value)
        if order_info is None:
            raise Exception('No order info found for tracking number {}'.format(tracking_num))
        packing_info = order_info['packing_info']
        return ShippingLabelOutputMeta.get_output_info(
            tracking_num.type, packing_info)

    def _get_username(self, tracking_num):
        order_info = self.tn_pi.get(tracking_num.value)
        return ShippingLabelOutputMeta.get_username(order_info['username'])

    def _get_output_page(self, output_infos):
        inch = 72
        buf = io.BytesIO()
        canvas = Canvas(buf, pagesize=(8.5*inch, 11*inch))

        for info in output_infos:
            canvas.saveState()
            x, y = info.translate
            # We flip the y coordinate since that's how PDF programs give us
            # the number of pixels from the top, not the bottom.
            y = 11*inch - y
            canvas.translate(x, y)
            if info.rotate != 0:
                canvas.rotate(info.rotate)

            t = canvas.beginText()
            t.setFont('Courier', 10)
            t.setTextOrigin(0, 0)
            t.textLines(info.text)
            canvas.drawText(t)

            canvas.restoreState()

        canvas.save()
        return PdfFileReader(buf).getPage(0)


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


def generate_tracking_num_to_packing_info_file():
    output_file = 'orders/tracking_num_to_packing_info.json'

    # Get order dict keyed by OrderID.
    orders = dict((o['OrderID'], o) for o in get_shipped_orders())

    result = json.load(open('orders/tracking_num_to_order_id.json'))
    keys = result.keys()
    for tracking_num in keys:
        order_ids = result[tracking_num]
        packing_info = '; '.join(orders[id]['packing_info'] for id in order_ids)
        username = orders[order_ids[0]]['username']
        result[tracking_num] = dict(
            username=username,
            order_ids=order_ids,
            packing_info=packing_info)

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
        str(pdf_file),
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


def get_blank_page():
    inch = 72
    return PageObject.createBlankPage(width=8.5*inch, height=11*inch)
