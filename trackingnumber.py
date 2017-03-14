import subprocess
import tempfile
from pathlib import Path
import re

import attr
from pyquery import PyQuery
from PyPDF2 import PdfFileWriter, PdfFileReader


@attr.s(repr=False)
class TrackingNumberReadMeta:
    """
    This class stores the bounding box for a particular type of tracking number.

    """
    entries = {}

    type = attr.ib(default='')
    # Coordinates where tracking number is found (left, top).
    coords = attr.ib(default=(0, 0))

    @classmethod
    def add_meta(cls, type, coords):
        s_coords = (str(coords[0]), str(coords[1]))
        cls.entries[s_coords] = TrackingNumberReadMeta(type=type, coords=coords)

    @classmethod
    def get(cls, coords):
        return cls.entries.get(coords)

    def __repr__(self):
        return 'TrackingNumberReadMeta<{}>'.format(self.type)


TrackingNumberReadMeta.add_meta(
    type='bulk-domestic-top',
    coords=(198, 677),
)
TrackingNumberReadMeta.add_meta(
    type='bulk-domestic-bottom',
    coords=(792, 677),
)
TrackingNumberReadMeta.add_meta(
    type='bulk-foreign',
    coords=(497, 528),
)
TrackingNumberReadMeta.add_meta(
    type='single-domestic',
    coords=(447, 624),
)
TrackingNumberReadMeta.add_meta(
    type='single-foreign',
    coords=(1, 1),      # need to fill out
)


@attr.s(repr=False)
class TrackingNumber:
    type = attr.ib(default='')
    value = attr.ib(default='')

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
            for page in get_all_html_pages_for_pdf(pdf_file):
                # Yield a list of tracking numbers for each page.
                page_results = []
                for elem in page.get_p_elements():
                    coords = self._get_coords(elem)
                    meta = TrackingNumberReadMeta.get(coords)
                    if meta is not None:
                        text = PyQuery(elem).text().replace('\xa0', '')
                        page_results.append(
                            TrackingNumber(type=meta.type, value=text)
                        )

                yield page_results

    def _get_input_files(self, dir_path):
        for pdf_file in dir_path.glob('*.pdf'):
            if not pdf_file.stem.endswith('-packing'):
                yield pdf_file

    def _get_coords(self, elem):
        text = elem.get('style')
        match = re.search(r'top:(\d+)px;left:(\d+)px;', text)
        top, left = match.groups()
        return left, top


class PdfPage:
    """
    DOM representation of a PDF page. Includes both the normal and rotated
    versions of the page.

    """
    def __init__(self, html, rotated_html):
        self.doc = PyQuery(remove_html_namespace(html))
        self.rotated_doc = PyQuery(remove_html_namespace(rotated_html))

    def get_p_elements(self):
        yield from self.doc('p')
        yield from self.rotated_doc('p')


def get_all_html_pages_for_pdf(pdf_file):
    html_seq = get_html_pages_for_pdf(pdf_file)
    rotated_pdf_file = create_rotated_pdf(pdf_file)
    rotated_html_seq = get_html_pages_for_pdf(rotated_pdf_file)
    for html, rotated_html in zip(html_seq, rotated_html_seq):
        yield PdfPage(html, rotated_html)


def get_html_pages_for_pdf(pdf_file):
    with tempfile.TemporaryDirectory() as dirpath:
        dirpath = Path(dirpath)
        cmd = [
            'pdftohtml', '-c', str(pdf_file), str(dirpath / 'output.html')]
        subprocess.check_call(cmd)
        for html_file in dirpath.glob('*.html'):
            if re.search(r'-\d+\.html$', html_file.name):
                yield html_file.read_text()


def create_rotated_pdf(pdf_file):
    """
    Create a copy of the given pdf file that is rotated, and return the path to
    the output file. The output file will be generated in a temp directory.

    """
    reader = PdfFileReader(pdf_file.open('rb'), strict=False)
    pages = (reader.getPage(i) for i in range(reader.numPages))

    handle, tmpfile = tempfile.mkstemp(suffix='.pdf')
    with open(tmpfile, 'wb') as fp:
        writer = PdfFileWriter()
        for page in pages:
            page.rotateCounterClockwise(90)
            writer.addPage(page)
        writer.write(fp)

    return tmpfile


def remove_html_namespace(html):
    """
    Removing the namespace from the HTML will allow PyQuery to use css
    selector queries.

    """
    return html.replace(
        'xmlns="http://www.w3.org/1999/xhtml" lang="" xml:lang=""', '')
