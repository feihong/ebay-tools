import json

from orders import download_shipped_orders, load_orders

from .db import Database


class TrackingNumberMapper:
    """
    Maps tracking numbers to output info.

    """
    def __init__(self, orders):
        self.db = Database()
        self.db.executescript("""
        create table orders(
            order_id string,
            packing_info string,
            username string,
            buyer string
        );
        create table order_tracking(
            order_id string,
            tracking_number string
        );
        """)
        self.add_orders(orders)

    def add_orders(self, orders):
        for order in orders:
            self.db.execute(
                'insert into orders ({fields}) values (?, ?, ?, ?)',
                ['order_id', 'packing_info', 'username', 'buyer'],
                order)
            for tracking_num in order['tracking_numbers']:
                self.db.execute(
                    'insert into order_tracking ({fields}) values (?, ?)',
                    ['order_id', 'tracking_number'],
                    [order['order_id'], tracking_num])

    def get_output(tracking_number):
        orders = self.db.select("""
            select {fields} from orders
            where order_id in (select order_id from order_tracking
                               where tracking_number = ?)""",
            ['order_id', 'packing_info', 'username', 'buyer'],
            tracking_number)

        if not orders:
            return None

        return dict(
            packing_info='; '.join(o['packing_info'] for o in orders),
            username=orders[0]['username'],
            notes=get_notes(orders))


def get_notes(orders):
    buyer = orders[0]['buyer']
    other_orders = select("""
        select packing_info from orders
        where buyer = ?
        and order_id not in (select order_id from order_tracking)""",
        (),
        buyer)

    if other_orders:
        stuff = '; '.join(r[0] for r in other_orders)
        return 'Buyer {buyer} also bought {stuff}'.format(
            buyer=buyer, stuff=stuff)
    else:
        return None


def get_shipped_orders():
    for user, orders in load_orders('shipped_orders.json')['payload'].items():
        for order in orders:
            yield order


def generate_simple_orders_file():
    result = []
    for order in get_shipped_orders():
        result.append(dict(
            order_id=order['OrderID'],
            packing_info=order['packing_info'],
            username=order['username'],
            buyer=order['BuyerUserID'],
            tracking_numbers=list(get_tracking_numbers_for_order(order)),
        ))

    with open('orders/shipped_orders_simple.json', 'w') as fp:
        json.dump(result, fp, indent=2)


def get_tracking_numbers_for_order(order):
    tracking_nums = set()

    transactions = order['TransactionArray']['Transaction']
    for transaction in transactions:
        try:
            details = transaction['ShippingDetails']['ShipmentTrackingDetails']
        except KeyError:
            details = []

        if not isinstance(details, list):
            details = [details]

        for detail in details:
            tn = detail['ShipmentTrackingNumber']
            tracking_nums.add(tn)

    return tracking_nums
