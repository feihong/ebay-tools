import json

from orders import download_shipped_orders, load_orders


class TrackingNumberMapper:
    """
    Maps tracking numbers to order information.

    """


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
