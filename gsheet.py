import csv
from pathlib import Path

import gspread
from oauth2client.service_account import ServiceAccountCredentials


def get_client():
    scopes = ['https://spreadsheets.google.com/feeds']
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        'service_account_key.json', scopes)
    return gspread.authorize(credentials)


def download_csv_files():
    client = get_client()
    spreadsheet = client.open('ebay items')
    worksheet_names = ['item_model', 'item_location']
    for name in worksheet_names:
        path = Path(name + '.csv')
        print('Writing {}'.format(path))
        worksheet = spreadsheet.worksheet(name)

        with path.open('w') as fp:
            writer = csv.writer(fp)
            for row in worksheet.get_all_values():
                writer.writerow(row)
