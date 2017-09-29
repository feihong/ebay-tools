import csv
import itertools
import json

from ebaysdk.trading import Connection as Trading

import config
import util


def rebuild_item_model_csv(output_file):
    items = list(get_items())
    items.sort(key=lambda x: x['model'])

    with open(output_file, 'w') as fp:
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

    print('Wrote {} rows to {}'.format(len(items), output_file))


def download_item_shipping_data(csv_file):
    items = list(get_items({
        'IncludeItemSpecifics': True,
        'OutputSelector': [
            'Item.Title',
            'Item.ItemSpecifics.NameValueList',
            'Item.ShippingPackageDetails',
            'Item.ShippingDetails',
        ]
    }))
    items.sort(key=lambda x: x['model'])

    # util.write_json(items, 'orders/temp_items.json')
    # items = util.read_json('orders/temp_items.json')

    with open(csv_file, 'w') as fp:
        fieldnames = ['user', 'model', 'title', 'url', 'weight',
            'domestic_shipping', 'intl_shipping']
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for item in items:
            row = dict(
                user=item['user'],
                model=item['model'],
                title=item['Title'],
                url='http://ebay.com/itm/' + item['item_id'],
                weight=get_weight(item),
                domestic_shipping=get_domestic_shipping(item),
                intl_shipping=get_intl_shipping(item),
            )
            writer.writerow(row)

    print('Wrote {} rows to {}'.format(len(items), csv_file))


def get_items():
    for dir_ in (p for p in config.BACKUP_PATH.iterdir() if p.is_dir()):
        user = dir_.stem
        for item_file in dir_.glob('*.json'):
            with item_file.open() as fp:
                item = json.load(fp)
                item.update(
                    item_id=item['ItemID'], user=user, model=get_model(item))
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
    if len(model) > 0:
        return model[0]
    else:
        return 'N/A'


def get_weight(item):
    spd = item['ShippingPackageDetails']
    lb = int(spd['WeightMajor']['value'])
    oz = int(spd['WeightMinor']['value'])
    return 16 * lb + oz


def get_domestic_shipping(item):
    sd = item['ShippingDetails']
    return sd['ShippingServiceOptions']['ShippingService']


def get_intl_shipping(item):
    sd = item['ShippingDetails']
    options = sd.get('InternationalShippingServiceOption')
    if options is not None:
        for option in sd['InternationalShippingServiceOption']:
            if option['ShipToLocation'] == 'CA':
                return option['ShippingService']
    else:
        return ''
