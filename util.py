from pathlib import Path

from mako.template import Template
from mako.lookup import TemplateLookup
from plim import preprocessor
import boto3


template_dir = Path(__file__).parent / 'templates'
lookup = TemplateLookup(
    directories=[str(template_dir)],
    preprocessor=preprocessor)


def render(filename, **kwargs):
    tmpl = lookup.get_template(filename)
    # tmpl = Template(
    #     filename=str(template_dir / filename), preprocessor=preprocessor)
    return tmpl.render(**kwargs)


def render_to_file(output_file, filename, **kwargs):
    with output_file.open('w') as fp:
        fp.write(render(filename, **kwargs))


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
    pprint(resp)
