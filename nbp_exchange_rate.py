from datetime import date, datetime, timedelta
import json
import sys
import logging
import requests
from flask import Flask
from logging.handlers import RotatingFileHandler
from flask_restful import Resource, Api
from jsonformatter import basicConfig
from paste.translogger import TransLogger
from waitress import serve

class ExchangeRate(Resource):
    def __init__(self, currencies_codes):
        self.currencies_codes = currencies_codes

    def __validate_input(self, currency, date_string):
        if currency.upper() not in self.currencies_codes:
            err = {
                'message': '400 Bad Request',
                'error': 'Incorrect currency.'}, 400
            logging.error(err)
            return err

        try:
            date_value = date.fromisoformat(date_string)
        except ValueError:
            err = {
                'message': '400 Bad Request',
                'error': 'Incorrect date string format. It should be YYYY-MM-DD.'}, 400
            logging.error(err)
            return err

        if date_value > datetime.now().date() or \
           date.fromisoformat('2002-01-02') > date_value:
            err = {
                'message': '400 Bad Request',
                'error': 'Incorrect date. Correct date is between 2002-01-03 and present.'}, 400
            logging.error(err)
            return err

        return None

    def __get_searched_data(self, currency, date_string):
        nbp_api_addr = f'https://api.nbp.pl/api/exchangerates/rates/a/{currency}'
        date_value = date.fromisoformat(date_string)
        for _ in range(7):
            date_value -= timedelta(days=1)
            nbp_api_addr += f'/{date_value}'

            try:
                req = requests.get(nbp_api_addr)
            except requests.exceptions.RequestException:
                err = {
                    'message': '502 Bad Gateway',
                    'error': 'The server got an invalid response while working as ' \
                        'a gateway to get the response needed to handle the request.'}, 500
                logging.error(err)
                return {'message': None, 'error': err}

            if req.status_code == 200:
                break
            nbp_api_addr = nbp_api_addr.rsplit('/', 1)[0]

        if req.status_code != 200:
            err = {
                'message': '500 Internal Server Error',
                'error': 'Failed to find data.'}, 500
            logging.error(err)
            return {'message': None, 'error': err}

        try:
            msg = json.loads(req.text)
        except json.decoder.JSONDecodeError:
            err = {
                'message': '500 Internal Server Error',
                'error': 'Failed to load data.'}, 500
            logging.error(err)
            return {'message': None, 'error': err}

        try:
            msg = {
                'message': 'Found exchange rates',
                'currency': f'{currency.upper()}',
                'searchedDate:': f'{date_string}',
                'effectiveDate': f'{msg["rates"][0]["effectiveDate"]}',
                'exchangeRate': f'{msg["rates"][0]["mid"]}'}
        except KeyError:
            err = {
                'message': '500 Internal Server Error',
                'error': 'Failed to format data.'}, 500
            logging.error(err)
            return {'message': None, 'error': err}

        return {'message': msg, 'error': None}


    def get(self, currency, date_string):
        err = self.__validate_input(currency, date_string)
        if err:
            return err

        msg = self.__get_searched_data(currency, date_string)
        if msg['error']:
            return msg['error']

        logging.info(msg['message'])
        return msg['message'], 200

def get_currencies_codes():
    table_a_addr = f'https://api.nbp.pl/api/exchangerates/tables/a'
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
    app = Flask(__name__)
    api = Api(app)
    api.add_resource(ExchangeRate, '/prevday/exchangerate/<string:currency>/<string:date_string>',
                     resource_class_kwargs={'currencies_codes': currencies_codes})
    return app

if __name__ == '__main__':
    STRING_FORMAT = '''{
        "asctime":         "asctime",
        "levelname":       "levelname",
        "name":            "name",
        "message":         "message"
    }'''
    file_handler = RotatingFileHandler('nbp_exchange_rate.log', maxBytes=100*10**6, backupCount=1)
    basicConfig(format=STRING_FORMAT, handlers=[file_handler, logging.StreamHandler()])
    logging.getLogger().setLevel(logging.INFO)

    app = create_app()
    if not app:
        sys.exit(1)

    app_logged = TransLogger(app, setup_console_handler=False)
    serve(app_logged, host='0.0.0.0', port='5000')

    sys.exit(0)
