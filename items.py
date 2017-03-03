import csv
import itertools
import json

from ebaysdk.trading import Connection as Trading

from config import EBAY_CREDENTIALS
import util


def download_item_model_data(csv_file):
    items = list(get_items({
        'IncludeItemSpecifics': True,
        'OutputSelector': [
            'Item.Title',
            'Item.ItemSpecifics.NameValueList',
        ]
    }))
    items.sort(key=lambda x: x['model'])

    # util.write_json(items, 'orders/temp_items.json')
    # items = util.read_json('orders/temp_items.json')

    with open(csv_file, 'w') as fp:
        fieldnames = ['model', 'item_id', 'title', 'user']
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for item in items:
            row = dict(
                model=item['model'],
                item_id=item['item_id'],
                title=item['Title'],
                user=item['user'],
            )
            writer.writerow(row)

    print('Wrote {} items to {}'.format(len(items), csv_file))


def get_items(params):
    for user, cred in EBAY_CREDENTIALS:
        request = ItemRequest(cred)
        for item_id in request.get_item_ids():
            print('Fetching item {}'.format(item_id))
            item = request.get_item(item_id, params)
            item.update(item_id=item_id, user=user, model=get_model(item))
            yield item


class ItemRequest:
    def __init__(self, credentials):
        self.trading = Trading(config_file=None, **credentials)

    def get_items(self, fields):
        for page_num in itertools.count(1):
            response = self._get_page(page_num, fields)
            activelist = response.reply.ActiveList
            page_count = int(activelist.PaginationResult.TotalNumberOfPages)
            print('Page {} of {}'.format(page_num, page_count))

            for item in response.dict()['ActiveList']['ItemArray']['Item']:
                yield item

            if page_count == page_num:
                break

    def get_item_ids(self):
        for item in self.get_items(fields=[]):
            yield item['ItemID']

    def get_item(self, item_id, params):
        params.update({'ItemID': item_id})
        response = self.trading.execute('GetItem', params)
        return response.dict()['Item']

    def _get_page(self, page_num, fields=[]):
        fields = fields + [
            'ActiveList.PaginationResult',
            'ActiveList.ItemArray.Item.ItemID',
        ]

        return self.trading.execute('GetMyeBaySelling', {
            'ActiveList': {
                'Include': True,
                'Pagination': {
                    'PageNumber': page_num
                }
            },
            'OutputSelector': fields,
        })


def get_model(item):
    model = [
        spec['Value']
        for spec in item['ItemSpecifics']['NameValueList']
        if spec['Name'] == 'Model'
    ]
    return model[0]
