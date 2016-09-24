"""
Check for orders that have been paid but have not been shipped.

"""
import arrow
from ebaysdk.trading import Connection as Trading
from ebaysdk.shopping import Connection as Shopping

import config


SHIPPING_URL_TEMPLATE = 'https://payments.ebay.com/ws/eBayISAPI.dll?PrintPostage&transactionid={transaction_id}&ssPageName=STRK:MESO:PSHP&itemid={item_id}'
SHIPPING_URL_TEMPLATE_2 = 'https://payments.ebay.com/ws/eBayISAPI.dll?PrintPostage&orderId={order_id}'



class OrderRequest:
    def __init__(self, credentials):
        self.credentials = credentials

    def get_orders(self):
        "Return a sequence of orders awaiting shipment"
        api = Trading(config_file=None, **self.credentials)
        yesterday = arrow.utcnow().replace(hours=-24)
        nowish = arrow.utcnow().replace(minutes=-2)
        response = api.execute('GetOrders', {
            'CreateTimeFrom': yesterday,
            'CreateTimeTo': nowish,
        })
        try:
            orders = response.reply.OrderArray.Order
        except AttributeError:
            orders = []

        for order in orders:
            if not hasattr(order, 'PaidTime'):
                continue
            if hasattr(order, 'ShippedTime'):
                continue
            yield order

    def get_orders_detail(self):
        "Return orders awaiting shipment, including item and address info."
        orders = list(self.get_orders())
        for order in orders:
            order.items = list(self.get_items(order))
            order.address = get_address(order)

            if '-' in order.OrderID:
                item_id, transaction_id = order.OrderID.split('-')
                url = SHIPPING_URL_TEMPLATE.format(
                    transaction_id=transaction_id, item_id=item_id)
            else:
                url = SHIPPING_URL_TEMPLATE_2.format(order_id=order.OrderID)
            order.shipping_url = url

        return orders

    def get_items(self, order):
        for transaction in order.TransactionArray.Transaction:
            item = transaction.Item
            item.model = self.get_model(item)
            item.quantity = int(transaction.QuantityPurchased)
            yield item

    def get_model(self, item):
        api = Shopping(config_file=None, **self.credentials)
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
