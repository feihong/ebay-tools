import csv
from pathlib import Path

import gspread
from oauth2client.service_account import ServiceAccountCredentials


def get_client():
    scopes = ['https://spreadsheets.google.com/feeds']
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        'service_account_key.json', scopes)
    return gspread.authorize(credentials)


def download_item_location_csv():
    client = get_client()
    spreadsheet = client.open('ebay items')
    name = 'item_location'
    output_path = Path(name + '.csv')
    worksheet = spreadsheet.worksheet(name)
    with output_path.open('w') as fp:
        writer = csv.writer(fp)
        for row in worksheet.get_all_values():
            writer.writerow(row)
    print(f'Downloaded {output_path}')
