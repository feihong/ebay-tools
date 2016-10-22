"""
Check for orders that have been paid but have not been shipped.

"""
from pathlib import Path
import json

import arrow
from ebaysdk.trading import Connection as Trading
from ebaysdk.shopping import Connection as Shopping

import config
from logger import log


SHIPPING_URL_TEMPLATE = 'https://payments.ebay.com/ws/eBayISAPI.dll?PrintPostage&transactionid={transaction_id}&ssPageName=STRK:MESO:PSHP&itemid={item_id}'
SHIPPING_URL_TEMPLATE_2 = 'https://payments.ebay.com/ws/eBayISAPI.dll?PrintPostage&orderId={order_id}'


def download_orders():
    """
    Download orders awaiting shipment.

    """
    order_count = 0
    result = {'content': {}}

    for user_id, cred in config.EBAY_CREDENTIALS:
        request = OrderRequest(cred)
        orders = request.get_orders_detail()
        result['content'][user_id] = orders
        order_count += len(orders)

    result['download_time'] = arrow.utcnow().format()

    orders_file = Path(config.ORDERS_DIR) / 'orders.json'
    with orders_file.open('w') as fp:
        json.dump(result, fp, indent=2)
    log('Downloaded {} orders to {}'.format(order_count, orders_file))


class OrderRequest:
    def __init__(self, credentials):
        self.credentials = credentials

    def get_orders(self):
        "Return a sequence of orders awaiting shipment"
        api = Trading(config_file=None, **self.credentials)
        few_days_ago = arrow.utcnow().replace(days=-5)
        # The API doesn't like time values that it thinks are in the future.
        nowish = arrow.utcnow().replace(minutes=-2)
        response = api.execute('GetOrders', {
            'CreateTimeFrom': few_days_ago,
            'CreateTimeTo': nowish,
        })
        try:
            # orders = response.reply.OrderArray.Order
            orders = response.dict()['OrderArray']['Order']
        except AttributeError:
            orders = ()

        for order in orders:
            if 'PaidTime' not in order:
                continue
            if 'ShippedTime' in order:
                continue

            log('{user}: {items}'.format(
                user=order['BuyerUserID'],
                items=get_items_text(order['items']))
            )
            yield order

    def get_orders_detail(self):
        "Return orders awaiting shipment, including item and address info."
        orders = list(self.get_orders())
        for order in orders:
            order['items'] = list(get_items(order, self.credentials))
            order['address'] = get_address(order)

            if '-' in order['OrderID']:
                item_id, transaction_id = order['OrderID'].split('-')
                url = SHIPPING_URL_TEMPLATE.format(
                    transaction_id=transaction_id, item_id=item_id)
            else:
                url = SHIPPING_URL_TEMPLATE_2.format(order_id=order['OrderID'])
            order['shipping_url'] = url

        return orders

    def get_order(self, order_id):
        api = Trading(config_file=None, **self.credentials)
        response = api.execute('GetOrders', {
            'OrderIDArray': [{'OrderID': order_id}]
        })
        return response.reply.OrderArray.Order[0]


def get_items_text(items):
    for item in items:
        yield '{} ({})'.format(item['model'], item['quantity'])


def get_items(order, cred):
    for transaction in order['TransactionArray']['Transaction']:
        item = transaction['Item']
        item['model'] = get_model(item['ItemID'], cred)
        item['quantity'] = int(transaction['QuantityPurchased'])
        yield item


def get_model(item_id, cred):
    api = Shopping(config_file=None, **cred)
    response = api.execute('GetSingleItem', {
        'ItemID': item_id,
        'IncludeSelector': 'ItemSpecifics'
    })
    item_specifics = response.reply.Item.ItemSpecifics.NameValueList
    for spec in item_specifics:
        if spec.Name == 'Model':
            return spec.Value
    return None


def get_address(order):
    sa = order['ShippingAddress']
    addr = (
        sa['Name'],
        sa['Street1'],
        sa['Street2'],
        '%s, %s %s' % (sa['CityName'], sa['StateOrProvince'], sa['PostalCode']),
        sa['CountryName'])
    return '\n'.join(line for line in addr if line is not None and line.strip())
