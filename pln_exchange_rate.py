import logging
import json
from logging.handlers import RotatingFileHandler
import sys
import requests
from flask import Flask
from flask_restful import Api
from jsonformatter import basicConfig
from paste.translogger import TransLogger
from waitress import serve
from resources.exchangerate import ExchangeRate

def get_currencies_codes():
    table_a_addr = 'https://api.nbp.pl/api/exchangerates/tables/a'
    try:
        req = requests.get(table_a_addr)
    except requests.exceptions.RequestException:
        return None

    if req.status_code != 200:
        return None

    try:
        table_a = json.loads(req.text)
    except json.decoder.JSONDecodeError:
        logging.error('Couldn\'t load json - table A.')
        return None

    currencies = table_a[0]['rates']
    currencies_codes = set()

    for currency in currencies:
        currencies_codes.add(currency['code'])

    return tuple(currencies_codes)

def create_app():
    currencies_codes = get_currencies_codes()
    if not currencies_codes:
        logging.error('Couldn\'t create currencies code list for table A.')
        return None
    new_app = Flask(__name__)
    api = Api(new_app)
    api.add_resource(ExchangeRate, '/prevday/exchangerate/<string:currency>/<string:date_string>',
                     resource_class_kwargs={'currencies_codes': currencies_codes})
    return new_app

if __name__ == '__main__':
    STRING_FORMAT = '''{
        "asctime":         "asctime",
        "levelname":       "levelname",
        "name":            "name",
        "message":         "message"
    }'''
    file_handler = RotatingFileHandler('pln_exchange_rate.log', maxBytes=100*10**6, backupCount=1)
    basicConfig(format=STRING_FORMAT, handlers=[file_handler, logging.StreamHandler()])
    logging.getLogger().setLevel(logging.INFO)

    app = create_app()
    if not app:
        sys.exit(1)

    app_logged = TransLogger(app, setup_console_handler=False)
    serve(app_logged, host='0.0.0.0', port='5000')

    sys.exit(0)
