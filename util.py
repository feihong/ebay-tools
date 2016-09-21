from pathlib import Path
from pprint import pprint

import arrow
import requests
from mako.template import Template
from mako.lookup import TemplateLookup
from plim import preprocessor
import boto3

import config


template_dir = Path(__file__).parent / 'templates'
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
