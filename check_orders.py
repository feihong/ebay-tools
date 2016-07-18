"""
Check for orders that have been paid but have not been shipped.

"""
import arrow
import datetime

from ebaysdk.trading import Connection as Trading

import config


def get_items(order):
    for transaction in order.TransactionArray.Transaction:
        yield transaction.Item


if __name__ == '__main__':
    api = Trading(config_file=None, **config.credentials)
    yesterday = arrow.utcnow().replace(hours=-24)
    nowish = arrow.utcnow().replace(minutes=-2)
    response = api.execute('GetOrders', {
        'CreateTimeFrom': yesterday,
        'CreateTimeTo': nowish,
    })

    count = 0
    orders = response.reply.OrderArray.Order
    # import ipdb; ipdb.set_trace()
    for order in orders:
        if not order.PaidTime:
            continue
        if hasattr(order, 'ShippedTime'):
            continue

        count += 1
        print('Buyer: ' + order.BuyerUserID)
        print('Status: ' + order.OrderStatus)
        print('Paid %s on %s' % (order.AmountPaid.value, order.PaidTime))
        print('Items:')
        for item in get_items(order):
            print('- ' + item.Title)
        sa = order.ShippingAddress
        addr = (sa.Name, sa.Street1, sa.Street2, sa.CityName, sa.CountryName,
                sa.PostalCode)
        addr = '\n'.join(line for line in addr if line is not None and line.strip())
        print('Address:')
        print(addr)
        print('='*80)

    print('%d orders created within the last 24 hours' % len(orders))
    print('%d orders awaiting shipment' % count)
