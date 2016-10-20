from postmen import Postmen, PostmenException

import config
from orders import OrderRequest


def make_label(credentials, order_id):
    request = OrderRequest(credentials)
    order = request.get_order(order_id)
    shipping_address = order.ShippingAddress
    ship_to = convert_address(shipping_address)
    print(ship_to)


ADDRESS_FIELD_MAPPING = {
    'Name': 'contact_name',
    'Phone': 'phone',
    'Street1': 'street1',
    'Street2': 'street2',
    'CityName': 'city',
    'StateOrProvince': 'state',
    'PostalCode': 'postal_code',
}.items()


def convert_address(shipping_address):
    """
    Given a shipping address object from eBay API, return an equivalent
    dictionary that will be acceptable to the Postmen API.

    """
    import pycountry
    country = pycountry.countries.get(alpha2=shipping_address.Country)

    ship_to = {'country': country.alpha3}

    for src, target in ADDRESS_FIELD_MAPPING:
        value = getattr(shipping_address, src, None)
        if value is not None:
            ship_to[target] = value

    return ship_to
