import datetime
import subprocess
from pathlib import Path

import httplib2
from oauth2client.service_account import ServiceAccountCredentials
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive


def combine_for_print(folder_title):
    drive = get_drive()
    filenames = []

    # Download all pdf files from GDrive.
    for i, fil in enumerate(get_pdf_files(drive, folder_title), 1):
        print(fil['title'])
        filename = '__temp-{}.pdf'.format(i)
        fil.GetContentFile(filename)
        filenames.append(filename)

    if not len(filenames):
        print('No pdf files were downloaded')
        return

    # Compute output name by using date and number of files.
    output_filename = '{:%Y-%m-%d %H%M} ({}).pdf'.format(
        datetime.datetime.now(), len(filenames))
    print('Combining files into {}'.format(output_filename))

    writer = PdfFileWriter()

    for i, filename in enumerate(filenames):
        reader = PdfFileReader(open(filename, 'rb'), strict=False)
        if (i % 2) == 0:    # if even page
            page = reader.getPage(0)
            writer.addPage(page)
        else:
            page.mergeTranslatedPage(reader.getPage(0), 0, -5*inch)

    with open(output_filename, 'wb') as fp:
        writer.write(fp)

    # Delete temp pdf files.
    subprocess.call('rm __temp-*.pdf', shell=True)


def download_and_combine(folder_title):
    drive = get_drive()
    filenames = []

    # Download all pdf files from GDrive.
    for i, fil in enumerate(get_pdf_files(drive, folder_title), 1):
        print(fil['title'])
        filename = '__temp-{}.pdf'.format(i)
        fil.GetContentFile(filename)
        filenames.append(filename)

    if not len(filenames):
        print('No pdf files were downloaded')
        return

    # Concatenate temp pdf files into a single pdf file.
    output_filename = '{:%Y-%m-%d %H%M} ({}).pdf'.format(
        datetime.datetime.now(), len(filenames))
    print('Combining files into {}'.format(output_filename))
    cmd = [
        'gs', '-dBATCH', '-dNOPAUSE', '-q', '-sDEVICE=pdfwrite',
        '-sOutputFile=' + output_filename]
    cmd.extend(filenames)
    subprocess.call(cmd)

    # Delete temp pdf files.
    subprocess.call('rm __temp-*.pdf', shell=True)


def get_drive():
    scopes = ['https://www.googleapis.com/auth/drive.readonly']
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        'service_account_key.json', scopes)
    credentials.authorize(httplib2.Http())

    gauth = GoogleAuth()
    gauth.credentials = credentials
    return GoogleDrive(gauth)


def get_pdf_files(drive, folder_title):
    query = "title = '{}'".format(folder_title)
    directory = drive.ListFile({'q': query}).GetList()[0]
    dir_id = directory['id']

    query = "'{}' in parents and trashed = false and mimeType = 'application/pdf'".format(dir_id)
    file_list = drive.ListFile({'q': query, 'orderBy': 'modifiedDate'}).GetList()
    for fil in file_list:
        yield fil
