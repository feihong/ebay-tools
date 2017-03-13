import subprocess
import tempfile
from pathlib import Path
import re

import attr
from pyquery import PyQuery
from PyPDF2 import PdfFileWriter, PdfFileReader


class TrackingNumberExtractor:
    pass


class PdfPage:
    """
    DOM representation of a PDF page. Includes both the normal and rotated
    versions of the page.

    """
    def __init__(self, html, rotated_html):
        self.doc = PyQuery(html)
        self.rotated_doc = PyQuery(rotated_html)

    def get_p_elements(self):
        yield from self.doc('p')
        yield from self.rotated_doc('p')


def get_html_pages(dir_path):
    for pdf_file in dir_path.glob('*.pdf'):
        if not pdf_file.stem.endswith('-packing'):
            for page in get_all_html_pages_for_pdf(pdf_file):
                yield page


def get_all_html_pages_for_pdf(pdf_file):
    html_seq = get_html_pages_for_pdf(pdf_file)
    rotated_pdf_file = create_rotated_pdf(pdf_file)
    rotated_html_seq = get_html_pages_for_pdf(pdf_file)
    for html, rotated_html in zip(html_seq, rotated_html_seq):
        yield PdfPage(html, rotated_html)


def get_html_pages_for_pdf(pdf_file):
    with tempfile.TemporaryDirectory() as dirpath:
        dirpath = Path(dirpath)
        cmd = [
            'pdftohtml', '-c', str(pdf_file), str(dirpath / 'output.html')]
        subprocess.check_call(cmd)
        for html_file in dirpath.glob('*.html'):
            if re.match(r'-\d+\.html$', html_file.name):
                yield html_file.read_text()


def create_rotated_pdf(pdf_file):
    """
    Create a copy of the given pdf file that is rotated, and return the path to
    the output file. The output file will be generated in a temp directory.

    """
    reader = PdfFileReader(pdf_file.open('rb'))
    pages = (reader.getPage(i) for i in range(reader.numPages))

    tmpfile = tempfile.mkstemp()
    with open(tmpfile, 'wb') as fp:
        writer = PdfFileWriter()
        for page in pages:
            page.rotateCounterClockwise(90)
            writer.addPage(page)
        writer.write(fp)

    return tmpfile
