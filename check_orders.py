"""
Check for orders that have been paid but have not been shipped.

"""
import arrow
from ebaysdk.trading import Connection as Trading
from ebaysdk.shopping import Connection as Shopping

import config


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

        orders = response.reply.OrderArray.Order
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
        return orders

    def get_items(self, order):
        for transaction in order.TransactionArray.Transaction:
            item = transaction.Item
            item.model = self.get_model(item)
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


# if __name__ == '__main__':
#     args = clint.arguments.Args()
#
#     orders = list(get_orders())
#     if len(orders):
#         if args.flags.contains('--send-text'):
#             send_text(
#                 config.SMS_NUMBER,
#                 '{} orders awaiting shipment'.format(len(orders)))
#
#         tmpl_file = Path(__file__).parent / 'check_orders.plim'
#         tmpl = Template(filename=str(tmpl_file), preprocessor=preprocessor)
#
#         orders.sort(key=lambda x: x.PaidTime, reverse=True)
#         with open(config.REPORT_PATH, 'w') as fp:
#             html = tmpl.render(
#                 updated_time=arrow.utcnow().to(config.TIME_ZONE),
#                 orders=orders,
#                 get_items=get_items,
#                 get_address=get_address)
#             fp.write(html)
