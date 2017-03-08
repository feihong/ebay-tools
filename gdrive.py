import httplib2
from oauth2client.service_account import ServiceAccountCredentials
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive


def get_drive():
    scopes = ['https://www.googleapis.com/auth/drive.readonly']
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        'service_account_key.json', scopes)
    credentials.authorize(httplib2.Http())

    gauth = GoogleAuth()
    gauth.credentials = credentials
    return GoogleDrive(gauth)


def get_file(drive, title):
    query = "title = '{}'".format(title)
    return drive.ListFile({'q': query}).GetList()[0]


def get_files_in_folder(drive, folder_title, mimetype):
    query = "title = '{}'".format(folder_title)
    directory = drive.ListFile({'q': query}).GetList()[0]
    dir_id = directory['id']

    # Retrieve all pdf files inside the given folder.
    query = "'{}' in parents and trashed = false and mimeType = '{}'".format(dir_id, mimetype)
    file_list = drive.ListFile({'q': query, 'orderBy': 'modifiedDate'}).GetList()
    for file_ in file_list:
        yield file_
