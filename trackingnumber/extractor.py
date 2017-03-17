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
    bbox=(147, 129, 10, 135),
)
TrackingNumberReadMeta.add_meta(
    type='bulk-domestic-bottom',
    bbox=(147, 524, 10, 135),
)
TrackingNumberReadMeta.add_meta(
    type='bulk-foreign',
    bbox=(324, 350, 140, 20),
)
TrackingNumberReadMeta.add_meta(
    type='single-domestic',
    bbox=(294, 431, 155, 12),
)
TrackingNumberReadMeta.add_meta(
    type='single-foreign',
    bbox=(1, 1, 3, 3),      # need to fill out
)


class InvalidTrackingNumber(Exception):
    pass


class TrackingNumber:
    type = attr.ib(default='')
    value = attr.ib(default='')

    def __init__(self, type, value):
        self.type = type

        prefix = 'USPSTRACKING#'
        if value.startswith(prefix):
            value = value[len(prefix):].strip()
        self.value = value

        if 'domestic' in type and not re.match(r'\d{22}', value):
            mesg = '{} is not a valid domestic tracking number'.format(value)
            raise InvalidTrackingNumber(mesg)

        if 'foreign' in type and not re.match(r'[A-Z]{2}\d{9}US', value):
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
            for i, page in enumerate(get_pages_for_pdf(pdf_file)):
                # Yield a list of tracking numbers for each page.
                yield list(self._get_tracking_numbers(page))

    def _get_input_files(self, dir_path):
        for pdf_file in dir_path.glob('*.pdf'):
            if not pdf_file.stem.endswith('-packing'):
                yield pdf_file

    def _get_tracking_numbers(self, page):
        result = defaultdict(list)

        for word in page.findall('word'):
            point = self._get_point(word)
            meta = TrackingNumberReadMeta.get(point)
            if meta is not None:
                result[meta.type].append(word.text)

        for k, v in result.items():
            try:
                yield TrackingNumber(type=k, value=''.join(v))
            except InvalidTrackingNumber:
                pass

    def _get_point(self, word):
        x = float(word.get('xMin'))
        y = float(word.get('yMin'))
        return x, y


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
