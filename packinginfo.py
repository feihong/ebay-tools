from datetime import datetime
import textwrap
import io

import attr
from reportlab.pdfgen.canvas import Canvas
from PyPDF2 import PdfFileReader, PdfFileWriter
from PyPDF2.pdf import PageObject

from trackingnumber import TrackingNumberExtractor, TrackingNumberMapper


@attr.s
class OutputMeta:
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
        cls.entries[type] = OutputMeta(type=type, **kwargs)

    @classmethod
    def get(cls, type):
        return cls.entries[type]

    @staticmethod
    def get_output_info(type, text):
        meta = OutputMeta.get(type)
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


OutputMeta.add_meta(
    type='bulk-domestic-top',
    translate=(244, 316),
    rotate=0,
    max_len=27,
    max_lines=2,
)
OutputMeta.add_meta(
    type='bulk-domestic-bottom',
    translate=(244, 713),
    rotate=0,
    max_len=27,
    max_lines=2,
)
OutputMeta.add_meta(
    type='bulk-foreign',
    translate=(537, 143),
    rotate=-90,
    max_len=21,
    max_lines=4,
)
OutputMeta.add_meta(
    type='single-domestic',
    translate=(223, 318),
    rotate=0,
    max_len=28,
    max_lines=2,
)
OutputMeta.add_meta(
    type='single-foreign',
    translate=(573, 165),
    rotate=-90,
    max_len=16,
    max_lines=5,
)
OutputMeta.add_meta(
    type='bulk-domestic-center-line',
    translate=(45, 397),
    rotate=0,
    max_len=None,
    max_lines=None,
)
OutputMeta.add_meta(
    type='username',
    translate=(45, 767),
    rotate=0,
    max_len=50,
    max_lines=1,
)
OutputMeta.add_meta(
    type='page-number',
    translate=(430, 767),
    rotate=0,
    max_len=30,
    max_lines=1,
)
OutputMeta.add_meta(
    type='bulk-domestic-top-notes',
    translate=(100, 347),
    rotate=0,
    max_len=73,
    max_lines=2,
)
OutputMeta.add_meta(
    type='bulk-domestic-bottom-notes',
    translate=(100, 740),
    rotate=0,
    max_len=73,
    max_lines=2,
)
OutputMeta.add_meta(
    type='bulk-foreign-notes',
    translate=(75, 645),
    rotate=0,
    max_len=79,
    max_lines=3,
)
OutputMeta.add_meta(
    type='single-domestic-notes',
    translate=(29, 646),
    rotate=0,
    max_len=83,
    max_lines=4,
)
OutputMeta.add_meta(
    type='single-foreign-notes',
    translate=(102, 634),
    rotate=0,
    max_len=83,
    max_lines=4,
)


@attr.s(repr=False)
class OutputInfo:
    text = attr.ib(default='xxx xxx')
    overflow = attr.ib(default=False)       # if text takes up too many lines
    translate = attr.ib(default=(10, 10))
    rotate = attr.ib(default=0)

    def __repr__(self):
        return '{} {}'.format(self.text, self.translate)


def get_center_line():
    return OutputMeta.get_output_info('bulk-domestic-center-line', '-  ' * 30)


def get_page_number(page_num, total, label_count):
    return OutputMeta.get_output_info(
        'page-number',
        'Page {} of {} ({} labels)'.format(page_num, total, label_count))


def get_username(text):
    return OutputMeta.get_output_info('username', 'User: {}'.format(text))


class PackingInfoWriter:
    def __init__(self, label_count=None, simple_orders_file=None):
        self.label_count = label_count
        self.extractor = TrackingNumberExtractor('.')
        self._set_input_pages()
        self.mapper = TrackingNumberMapper(simple_orders_file)

    def write_output_file(self, output_file=None):
        writer = PdfFileWriter()
        output_pages = self.get_output_pages()

        for input_page, output_page in zip(self.input_pages, output_pages):
            input_page.mergePage(output_page)
            writer.addPage(input_page)

        if output_file is None:
            output_file = '{:%Y-%m-%d %H%M} ({})+packing.pdf'.format(
                datetime.now(), self.label_count)
        with open(output_file, 'wb') as fp:
            writer.write(fp)
        print('Wrote output to ' + output_file)

    def get_output_pages(self):
        for infos in self.get_output_infos():
            yield self._get_output_page(infos)

    def get_output_infos(self):
        result = []

        tracking_num_collection = list(self.extractor.get_tracking_numbers())
        page_count = len(tracking_num_collection)
        if self.label_count is None:
            self.label_count = sum(len(lst) for lst in tracking_num_collection)

        for i, tracking_numbers in enumerate(tracking_num_collection, 1):
            output_infos = list(self._get_output_infos(tracking_numbers))

            username = self._get_username(tracking_numbers)
            if username:
                output_infos.append(get_username(username))

            output_infos.append(get_page_number(i, page_count, self.label_count))

            if len(tracking_numbers) >= 2:
                output_infos.append(get_center_line())

            result.append(output_infos)

        return result

    def _set_input_pages(self):
        self.input_pages = []

        for pdf_file in self.extractor.input_files:
            # EBay label PDFs are a bit weird, so set strict to False.
            reader = PdfFileReader(pdf_file.open('rb'), strict=False)
            for page_index in range(0, reader.numPages):
                page = reader.getPage(page_index)
                height = page.mediaBox[3]
                if height == (5.5 * 72):
                    # This is a half-size page, so make it full size.
                    page2 = get_blank_page()
                    page2.mergeTranslatedPage(page, tx=0, ty=5.5*72)
                    page = page2
                self.input_pages.append(page)

    def _get_output_infos(self, tracking_numbers):
        for tn in tracking_numbers:
            output = self.mapper.get_output(tn.value)
            if output is None:
                tmpl = 'Found no orders linked to {} tracking number {} on page {} of {}'
                mesg = tmpl.format(tn.type, tn.value, tn.page_number, tn.input_file)
                raise Exception(mesg)
            yield OutputMeta.get_output_info(tn.type, output['packing_info'])

            notes = output['notes']
            if notes:
                yield OutputMeta.get_output_info(
                    tn.type + '-notes', 'Notes: ' + notes)

    def _get_username(self, tracking_numbers):
        for tn in tracking_numbers:
            output = self.mapper.get_output(tn.value)
            return output['username']

        return None

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


def get_blank_page():
    inch = 72
    return PageObject.createBlankPage(width=8.5*inch, height=11*inch)
