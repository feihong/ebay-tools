import csv
import itertools

from ebaysdk.trading import Connection as Trading

from config import EBAY_CREDENTIALS


def download_item_model_data(csv_file):
    items = list(get_items())
    items.sort(key=lambda x: x['model'])

    with open(csv_file, 'w') as fp:
        fieldnames = ['model', 'item_id', 'title', 'user']
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for item in items:
            writer.writerow(item)

    print('Wrote {} items to {}'.format(len(items), csv_file))


def get_items():
    for user, cred in EBAY_CREDENTIALS:
        request = ItemRequest(cred)
        for item_id in request.get_item_ids():
            ebay_item = request.get_item(item_id)
            yield dict(
                item_id=item_id,
                user=user,
                model=get_model(ebay_item),
                title=ebay_item.Title,
            )


class ItemRequest:
    def __init__(self, credentials):
        self.trading = Trading(config_file=None, **credentials)

    def get_page(self, page_num):
        return self.trading.execute('GetMyeBaySelling', {
            'ActiveList': {
                'Include': True,
                'Pagination': {
                    'PageNumber': page_num
                }
            },
            'OutputSelector': [
                'ActiveList.PaginationResult',
                'ActiveList.ItemArray.Item.ItemID',
            ]
        })

    def get_item_ids(self):
        for page_num in itertools.count(1):
            print('Page %s' % page_num)
            response = self.get_page(page_num)
            activelist = response.reply.ActiveList
            page_count = int(activelist.PaginationResult.TotalNumberOfPages)
            for item in activelist.ItemArray.Item:
                yield item.ItemID
            if page_count == page_num:
                break

    def get_item(self, item_id):
        response = self.trading.execute('GetItem', {
            'ItemID': item_id,
            'IncludeItemSpecifics': True,
             'OutputSelector': [
                'Item.Title',
                'Item.ItemSpecifics.NameValueList',
            ]
        })
        return response.reply.Item


def get_model(item):
    model = [
        spec.Value
        for spec in item.ItemSpecifics.NameValueList
        if spec.Name == 'Model'
    ]
    return model[0]
