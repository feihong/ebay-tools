import subprocess
from pathlib import Path
import re
from collections import defaultdict

import attr
from lxml import etree
from PyPDF2 import PdfFileWriter, PdfFileReader


@attr.s(repr=False)
class TrackingNumberReadMeta:
    """
    This class stores the bounding box for a particular type of tracking number.

    """
    entries = []

    type = attr.ib(default='')
    # Bounding box where tracking number is found (left, top, width, height).
    bbox = attr.ib(default=(0, 0, 0, 0))

    @classmethod
    def add_meta(cls, type, bbox):
        point = bbox[:2]
        cls.entries.append(TrackingNumberReadMeta(type=type, bbox=bbox))

    @classmethod
    def get(cls, coords):
        for meta in cls.entries:
            if contains(meta.bbox, coords):
                return meta

        return None

    def __repr__(self):
        return 'TrackingNumberReadMeta<{}>'.format(self.type)


TrackingNumberReadMeta.add_meta(
    type='bulk-domestic-top',
    bbox=(150, 129, 20, 140),
)
TrackingNumberReadMeta.add_meta(
    type='bulk-domestic-bottom',
    bbox=(150, 518, 20, 140),
)
TrackingNumberReadMeta.add_meta(
    type='bulk-foreign',
    bbox=(295, 350, 200, 25),
)
TrackingNumberReadMeta.add_meta(
    type='single-domestic',
    bbox=(294, 429, 155, 12),
    # bbox=(309, 448, 160, 16),
)
# It's too hard to get these to work without intersecting with other types of
# labels. You'll have to manually add these to the label.
# TrackingNumberReadMeta.add_meta(
#     type='single-foreign',
#     bbox=(355, 370, 110, 15),
# )


class InvalidTrackingNumber(Exception):
    pass


class TrackingNumber:
    def __init__(self, type, value, input_file, page_number):
        self.type = type
        self.input_file = input_file
        self.page_number = page_number
        self.value = value

        if 'domestic' in type and not is_domestic_tracking_number(value):
            mesg = '{} is not a valid domestic tracking number'.format(value)
            raise InvalidTrackingNumber(mesg)

        if 'foreign' in type and not is_foreign_tracking_number(value):
            mesg = '{} is not a valid foreign tracking number'.format(value)
            raise InvalidTrackingNumber(mesg)

    def __repr__(self):
        return '{}:{}'.format(self.type, self.value)


class TrackingNumberExtractor:
    def __init__(self, dir_path):
        dir_path = Path(dir_path)
        self.input_files = list(self._get_input_files(dir_path))

        mesg = ', '.join(str(f) for f in self.input_files)
        print('Input files: ' + mesg)

    def get_tracking_numbers(self):
        for pdf_file in self.input_files:
            for i, page in enumerate(get_pages_for_pdf(pdf_file), 1):
                # Yield a list of tracking numbers for each page.
                yield list(self._get_tracking_numbers(page, str(pdf_file), i))

    def _get_input_files(self, dir_path):
        for pdf_file in dir_path.glob('*.pdf'):
            if not pdf_file.stem.endswith('+packing'):
                yield pdf_file

    def _get_tracking_numbers(self, page, input_file, page_number):
        result = defaultdict(list)

        for word in page.findall('word'):
            point = self._get_point(word)
            meta = TrackingNumberReadMeta.get(point)
            if meta is not None:
                result[meta.type].append(word.text)

        for type, values in result.items():
            try:
                yield TrackingNumber(
                    type, ''.join(values), input_file, page_number)
            except InvalidTrackingNumber as err:
                pass

    def _get_point(self, word):
        x = float(word.get('xMin'))
        y = float(word.get('yMin'))
        return x, y


def is_domestic_tracking_number(value):
    return re.match(r'\d{22}', value)


def is_foreign_tracking_number(value):
    return re.match(r'\d{22}', value) or re.match(r'[A-Z]{2}\d{9}US', value)



def get_pages_for_pdf(pdf_file):
    cmd = ['pdftotext', '-bbox', str(pdf_file), '-']
    html = subprocess.check_output(cmd).decode('utf-8')
    html = remove_html_namespace(html)
    root = etree.fromstring(html)
    return root.findall('body/doc/page')


def remove_html_namespace(html):
    """
    Removing the namespace from the HTML will us to use xpath selectors more
    easily in lxml.etree.

    """
    return html.replace('xmlns="http://www.w3.org/1999/xhtml"', '')


def contains(bbox, point):
    x, y, w, h = bbox
    return x <= point[0] <= (x+w) and y <= point[1] <= (y+h)
