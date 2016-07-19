"""
Check for orders that have been paid but have not been shipped.

"""
import arrow
import datetime

import requests
from mako.template import Template
from plim import preprocessor
from ebaysdk.trading import Connection as Trading
from ebaysdk.shopping import Connection as Shopping

import config


def get_orders():
    api = Trading(config_file=None, **config.credentials)
    yesterday = arrow.utcnow().replace(hours=-24)
    nowish = arrow.utcnow().replace(minutes=-2)
    response = api.execute('GetOrders', {
        'CreateTimeFrom': yesterday,
        'CreateTimeTo': nowish,
    })

    count = 0
    orders = response.reply.OrderArray.Order
    for order in orders:
        if not hasattr(order, 'PaidTime'):
            continue
        # if hasattr(order, 'ShippedTime'):
        #     continue

        count += 1
        print('Buyer: ' + order.BuyerUserID)
        print('Status: ' + order.OrderStatus)
        print('Paid %s on %s' % (order.AmountPaid.value, order.PaidTime))
        print('Items:')
        for item in get_items(order):
            print('- %s => %s' % (item.Title, item.Model))
        print('Address:')
        print(get_address(order))
        print('='*80)
        yield order

    print('%d orders created within the last 24 hours' % len(orders))
    print('%d orders awaiting shipment' % count)


def get_items(order):
    for transaction in order.TransactionArray.Transaction:
        item = transaction.Item
        item.Model = get_model(item)
        yield item


def get_model(item):
    api = Shopping(config_file=None, **config.credentials)
    response = api.execute('GetSingleItem', {
        'ItemID': item.ItemID,
        'IncludeSelector': 'ItemSpecifics'
    })
    item_specifics = response.reply.Item.ItemSpecifics.NameValueList
    for spec in item_specifics:
        if spec.Name == 'Model':
            return spec.Value
    return None


def get_address(order):
    sa = order.ShippingAddress
    addr = (sa.Name, sa.Street1, sa.Street2,
            '%s, %s %s' % (sa.CityName, sa.StateOrProvince, sa.PostalCode),
            sa.CountryName)
    return '\n'.join(line for line in addr if line is not None and line.strip())



def send_text(order_count):
    data = dict(
        number=config.SMS_NUMBER,
        message='%d orders awaiting shipment' % order_count)
    requests.post('http://textbelt.com/text', data)


if __name__ == '__main__':
    orders = list(get_orders())
    if len(orders):
        tmpl = Template(filename='check_orders.plim', preprocessor=preprocessor)
        with open(config.REPORT_PATH, 'w') as fp:
            html = tmpl.render(
                orders=orders,
                get_items=get_items,
                get_address=get_address)
            fp.write(html)
