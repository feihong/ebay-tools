from pathlib import Path
from pprint import pprint
import csv
import json

import arrow
import requests
from mako.template import Template
from mako.lookup import TemplateLookup
from plim import preprocessor
import boto3

import config


here = Path(__file__).parent
template_dir = here / 'templates'
lookup = TemplateLookup(
    directories=[str(template_dir)],
    preprocessor=preprocessor)


def render(filename, **kwargs):
    tmpl = lookup.get_template(filename)
    return tmpl.render(**kwargs)


def render_to_file(output_file, template_file, **kwargs):
    with output_file.open('w') as fp:
        fp.write(render(template_file, **kwargs))


def send_email(recipient, subject, body):
    domain, private_key = config.MAILGUN_PARAMS.split(';')
    url = 'https://api.mailgun.net/v3/{}/messages'.format(domain)

    resp = requests.post(
        url,
        auth=('api', private_key),
        data={
            'from': 'OrderMaster <overlord@{}>'.format(domain),
            'to': recipient,
            'subject': subject,
            'text': body,
        },
    )
    print(resp.text)


def send_sms(number, message):
    access_key, secret_key = config.AWS_PARAMS.split(';')
    client = boto3.client(
        'sns',
        region_name='us-east-1',
        **config.AWS_CREDENTIALS,
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
    pprint(resp)


def local_now():
    return arrow.utcnow().to(config.TIME_ZONE)


def str_to_local_time(text):
    return arrow.get(text).to(config.TIME_ZONE)


def get_item_metadata_map():
    """
    Return a dict where the keys are models and the values are dicts.

    """
    result = {}
    with (here / 'item_location.csv').open() as fp:
        for row in csv.DictReader(fp):
            model = row['Model'].lower()
            result[model] = row

    return result


item_metadata_map = get_item_metadata_map()


def get_notes_for_item(model):
    d = item_metadata_map.get(model)
    return d['Notes'] if d else None


def get_item_model_map():
    result = {}
    with (here / 'item_model.csv').open() as fp:
        for row in csv.DictReader(fp):
            item_id = row['item_id']
            result[item_id] = row['model']
    return result


item_model_map = get_item_model_map()


def get_model_for_item(item_id):
    return item_model_map.get(item_id, '?')


def get_weight_from_model(model):
    try:
        code = model.rsplit('-', 1)[1]
        if code.endswith('b'):
            code = code[:-1]
            if '.' in code:
                lb, oz = code.split('.')
            else:
                lb, oz = code, '0'
            return float(lb) * 16 + float(oz)
        else:
            return float(code)
    except:
        return None


def get_total_weight_of_orders(orders):
    def gen():
        for order in orders:
            for item in order['items']:
                yield item['weight']

    return sum(gen())


def get_packing_info(order):
    result = []

    for item in order['items']:
        if item['quantity'] > 1:
            text = '{quantity}x {model}'.format(**item)
        else:
            text = item['model']

        meta = item_metadata_map.get(item['model'], {'Location': '_'})
        text += ' ' + meta['Location']
        result.append(text)

    return ', '.join(result)


def write_json(obj, json_file):
    with open(json_file, 'w') as fp:
        json.dump(obj, fp, indent=2)


def read_json(json_file):
    with open(json_file) as fp:
        return json.load(fp)
