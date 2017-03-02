"""
Check for orders that have been paid but have not been shipped.

"""
from pathlib import Path
import json
import itertools

import arrow
from ebaysdk.trading import Connection as Trading
from ebaysdk.shopping import Connection as Shopping

import config
import util
from logger import log


SHIPPING_URL_TEMPLATE = 'https://payments.ebay.com/ws/eBayISAPI.dll?PrintPostage&transactionid={transaction_id}&ssPageName=STRK:MESO:PSHP&itemid={item_id}'
SHIPPING_URL_TEMPLATE_2 = 'https://payments.ebay.com/ws/eBayISAPI.dll?PrintPostage&orderId={order_id}'
DAYS_BACK = 10


def download_orders_awaiting_shipment():
    """
    Download orders awaiting shipment.

    """
    download_orders('orders.json', 'get_orders_awaiting_shipment')


def download_shipped_orders(output_file='shipped_orders.json'):
    """
    Download orders that have been marked as shipped (i.e. their shipping labels
    have been printed).

    """
    download_orders(output_file, 'get_shipped_orders')


def download_orders(output_file, method):
    order_count = 0
    result = dict(payload={})

    for user_id, cred in config.EBAY_CREDENTIALS:
        request = OrderRequest(cred)
        get_orders = getattr(request, method)
        orders = list(get_orders())
        result['payload'][user_id] = orders
        order_count += len(orders)

    result['download_time'] = arrow.utcnow().format()

    orders_file = Path(config.ORDERS_DIR) / output_file
    with orders_file.open('w') as fp:
        json.dump(result, fp, indent=2)

    log('Downloaded {} orders to {}'.format(order_count, orders_file))


def load_orders(json_file):
    orders_file = Path(config.ORDERS_DIR) / json_file
    with orders_file.open() as fp:
        result = json.load(fp)
        # Convert download_time to a datetime object.
        result['download_time'] = util.str_to_local_time(result['download_time'])

        for username, orders in result['payload'].items():
            for order in orders:
                order['PaidTime'] = util.str_to_local_time(order['PaidTime'])
                order['items'] = list(get_items(order))
                order['packing_info'] = util.get_packing_info(order)
                order['address'] = get_address(order)
                order['shipping_url'] = get_shipping_url(order)
                order['username'] = username

        return result


class OrderRequest:
    def __init__(self, credentials):
        self.credentials = credentials
        self.api = Trading(config_file=None, **self.credentials)

    def get_orders_awaiting_shipment(self):
        for order in self.get_orders(days_back=1):
            # Only yield orders that haven't yet been shipped.
            if 'ShippedTime' not in order:
                yield order

    def get_shipped_orders(self):
        for order in self.get_orders(days_back=1):
            # Only yield orders that have been shipped.
            if 'ShippedTime' in order:
                yield order

    def get_orders(self, days_back=DAYS_BACK):
        self.start = arrow.utcnow().replace(days=-days_back)
        # The API doesn't like time values that it thinks are in the future.
        self.end = arrow.utcnow().replace(minutes=-1)

        for page in itertools.count(1):
            response = self._get_orders_for_page(page)
            reply = response.reply
            print('Page {}, {} items'.format(page, reply.ReturnedOrderCountActual))

            rdict = response.dict()
            if 'OrderArray' in rdict:
                orders = rdict['OrderArray']['Order']
            else:
                orders = ()

            for order in orders:
                # Ignore orders that haven't been paid.
                if 'PaidTime' not in order:
                    continue
                yield order

            if reply.PageNumber == reply.PaginationResult.TotalNumberOfPages:
                break

    def get_orders_detail(self):
        "Return orders awaiting shipment, including item and address info."
        orders = list(self.get_orders_awaiting_shipment())
        for order in orders:
            order['items'] = list(get_items(order))
            order['address'] = get_address(order)

            if '-' in order['OrderID']:
                item_id, transaction_id = order['OrderID'].split('-')
                url = SHIPPING_URL_TEMPLATE.format(
                    transaction_id=transaction_id, item_id=item_id)
            else:
                url = SHIPPING_URL_TEMPLATE_2.format(order_id=order['OrderID'])
            order['shipping_url'] = url

            log('{user}: {items}'.format(
                user=order['BuyerUserID'],
                items=', '.join(get_items_text(order['items'])))
            )

        return orders

    def get_order(self, order_id):
        api = Trading(config_file=None, **self.credentials)
        response = api.execute('GetOrders', {
            'OrderIDArray': [{'OrderID': order_id}]
        })
        return response.reply.OrderArray.Order[0]

    def _get_orders_for_page(self, page):
        """
        Return the response object for a single page.

        """
        response = self.api.execute('GetOrders', {
            'CreateTimeFrom': self.start,
            'CreateTimeTo': self.end,
            'OrderStatus': 'Completed',
            'Pagination': {
                'PageNumber': page,
                'EntriesPerPage': 100,
            }
        })
        if page == 1:
            pagination = response.reply.PaginationResult
            print('Found {} orders over {} pages'.format(
                pagination.TotalNumberOfEntries, pagination.TotalNumberOfPages))
        return response


def get_items(order):
    for transaction in order['TransactionArray']['Transaction']:
        item = transaction['Item']
        item['model'] = util.get_model_for_item(item['ItemID'])
        item['quantity'] = int(transaction['QuantityPurchased'])
        item['notes'] = util.get_notes_for_item(item['model'])
        yield item


def get_items_text(items):
    for item in items:
        yield '{} ({})'.format(item['model'], item['quantity'])


def get_address(order):
    sa = order['ShippingAddress']
    addr = (
        sa['Name'],
        sa['Street1'],
        sa['Street2'],
        '%s, %s %s' % (sa['CityName'], sa['StateOrProvince'], sa['PostalCode']),
        sa['CountryName'])
    return '\n'.join(line for line in addr if line is not None and line.strip())


def get_shipping_url(order):
    if '-' in order['OrderID']:
        item_id, transaction_id = order['OrderID'].split('-')
        return SHIPPING_URL_TEMPLATE.format(
            transaction_id=transaction_id, item_id=item_id)
    else:
        return SHIPPING_URL_TEMPLATE_2.format(order_id=order['OrderID'])


def hours_since(dt):
    "Return the number of hours since given datetime"
    if isinstance(dt, str):
        dt = arrow.get(dt)
    delta = arrow.utcnow() - dt
    return delta.total_seconds() / 3600
