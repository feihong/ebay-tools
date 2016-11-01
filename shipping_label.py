from io import BytesIO
from PyPDF2 import PdfFileWriter, PdfFileReader
from PIL import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas


def process_return_label(pdf_file):
    image = list(get_images(pdf_file))[0]
    image_reader = ImageReader(image)

    with open(pdf_file, 'wb') as fp:
        writer = PdfFileWriter()
        writer.addPage(get_image_page(image_reader))
        writer.write(fp)


def get_images(pdf_file):
    with open(pdf_file, 'rb') as fp:
        reader = PdfFileReader(fp)
        page = reader.getPage(0)
        xObject = page['/Resources']['/XObject'].getObject()

        for obj in xObject:
            if xObject[obj]['/Subtype'] == '/Image':
                width, height = (xObject[obj]['/Width'], xObject[obj]['/Height'])
                # Ignore smaller images.
                if height < 100:
                    continue

                size = width, height
                data = xObject[obj].getData()
                if xObject[obj]['/ColorSpace'] == '/DeviceRGB':
                    mode = "RGB"
                else:
                    mode = "P"

                encoding = xObject[obj]['/Filter']
                if encoding == '/FlateDecode':
                    yield Image.frombytes(mode, size, data)
                else:
                    raise Exception(
                        'Unexpected image encoding: {}'.format(encoding))


def get_image_page(image):
    inch = 72
    bio = BytesIO()
    c = Canvas(bio, pagesize=(8.5*inch, 11*inch))
    dim = c.drawImage(image, inch, 5.5*inch, 6*inch, 4*inch)
    # print(dim)
    c.save()
    return PdfFileReader(bio).getPage(0)
