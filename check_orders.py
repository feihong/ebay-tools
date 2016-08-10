"""
Check for orders that have been paid but have not been shipped.

"""
import datetime
from pathlib import Path
from pprint import pprint

import arrow
import boto3
import requests
from mako.template import Template
from plim import preprocessor
import clint.arguments
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


def send_text(number, message):
    access_key, secret_key = config.AWS_PARAMS.split(';')
    client = boto3.client(
        'sns',
        region_name='us-east-1',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )
    resp = client.publish(
        PhoneNumber=number,
        Message=message,
        MessageAttributes={
            'SMSType': {
                'StringValue': 'Promotional',
                'DataType': 'String',
            }
        }
    )
    # pprint(resp)


if __name__ == '__main__':
    args = clint.arguments.Args()

    orders = list(get_orders())
    if len(orders):
        if args.flags.contains('--send-text'):
            send_text(
                config.SMS_NUMBER,
                '{} orders awaiting shipment'.format(len(orders)))

        tmpl_file = Path(__file__).parent / 'check_orders.plim'
        tmpl = Template(filename=str(tmpl_file), preprocessor=preprocessor)

        orders.sort(key=lambda x: x.PaidTime, reverse=True)
        with open(config.REPORT_PATH, 'w') as fp:
            html = tmpl.render(
                updated_time=arrow.utcnow().to(config.TIME_ZONE),
                orders=orders,
                get_items=get_items,
                get_address=get_address)
            fp.write(html)
