from io import BytesIO
from PyPDF2 import PdfFileWriter, PdfFileReader
from PIL import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas


def crop_shipping_label(pdf_file):
    output = PdfFileWriter()
    output.addPage(get_cropped_page(pdf_file))

    with open('cropped_label.pdf', 'wb') as fp:
        output.write(fp)


def get_cropped_page(pdf_file):
    fp = open(pdf_file, 'rb')
    # Set strict to False because document may not have unique keys.
    reader = PdfFileReader(fp, strict=False)
    page = reader.getPage(0)
    page.mediaBox.lowerLeft = (65, 445)
    page.mediaBox.upperRight = (540, 750)
    return page


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
                if encoding == '/FlateDecode' or '/FlateDecode' in encoding:
                    yield Image.frombytes(mode, size, data)
                else:
                    raise Exception(
                        'Unexpected image encoding: {}'.format(encoding))


def get_image_page(image):
    inch = 72
    bio = BytesIO()
    c = Canvas(bio, pagesize=(8.5*inch, 11*inch))
    dim = c.drawImage(image, 0.5*inch, 6.3*inch, 495, 290)
    # print(dim)
    c.save()
    return PdfFileReader(bio).getPage(0)
