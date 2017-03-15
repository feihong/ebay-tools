import json

from orders import download_shipped_orders, load_orders

from .db import Database


class TrackingNumberMapper:
    """
    Maps tracking numbers to output info.

    """
    def __init__(self, simple_orders_file=None):
        self.db = Database()
        self.db.executescript("""
        create table orders(
            order_id text,
            packing_info text,
            username text,
            buyer text
        );
        create table order_tracking(
            order_id text,
            tracking_number text,
            primary key(order_id, tracking_number)
        );
        """)

        if simple_orders_file is None:
            orders = get_simple_orders()
        else:
            orders = json.load(open(simple_orders_file))

        self.add_orders(orders)

    def add_orders(self, orders):
        for order in orders:
            self.db.execute(
                'insert into orders ({fields}) values (?, ?, ?, ?)',
                ['order_id', 'packing_info', 'username', 'buyer'],
                order)

            for tracking_num in order['tracking_numbers']:
                try:
                    self.db.execute(
                        'insert into order_tracking ({fields}) values (?, ?)',
                        ['order_id', 'tracking_number'],
                        [order['order_id'], tracking_num])
                except Exception as ex:
                    print(ex)
                    import ipdb; ipdb.set_trace()

    def get_output(self, tracking_number):
        orders = self.db.select("""
            select {fields} from orders
            where order_id in (select order_id from order_tracking
                               where tracking_number = ?)""",
            ['order_id', 'packing_info', 'username', 'buyer'],
            tracking_number)

        if not orders:
            mesg = 'Found no orders linked to tracking number {}'.format(tracking_number)
            raise Exception(mesg)

        return dict(
            packing_info='; '.join(o['packing_info'] for o in orders),
            username=orders[0]['username'],
            notes=self._get_notes(orders))

    def _get_notes(self, orders):
        buyer = orders[0]['buyer']
        other_orders = self.db.select("""
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


def get_simple_orders():
    result = []
    for order in get_shipped_orders():
        result.append(dict(
            order_id=order['OrderID'],
            packing_info=order['packing_info'],
            username=order['username'],
            buyer=order['BuyerUserID'],
            tracking_numbers=list(get_tracking_numbers_for_order(order)),
        ))
    return result


def generate_simple_orders_file():
    with open('orders/shipped_orders_simple.json', 'w') as fp:
        result = get_simple_orders()
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
