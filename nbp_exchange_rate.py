from datetime import date, datetime, timedelta
import json
import sys
import logging
import requests
from flask import Flask
from flask_restful import Resource, Api
from paste.translogger import TransLogger
from waitress import serve

class ExchangeRate(Resource):
    def __init__(self, currencies_codes):
        self.currencies_codes = currencies_codes
        self.date_value = None
        self.err = None

    def __validate_input(self, currency, date_string):
        if currency.upper() not in self.currencies_codes:
            self.err = {
                'message': '400 Bad Request',
                'error': 'Incorrect currency.'}, 400
            return None

        try:
            self.date_value = date.fromisoformat(date_string)
        except ValueError:
            self.err = {
                'message': '400 Bad Request',
                'error': 'Incorrect date string format. It should be YYYY-MM-DD.'}, 400
            return None

        if self.date_value > datetime.now().date() or \
           date.fromisoformat('2002-01-02') > self.date_value:
            self.err = {
                'message': '400 Bad Request',
                'error': 'Incorrect date. Correct date is between 2002-01-03 and present.'}, 400
            return None

        return None

    def __get_searched_data(self, currency, date_string):
        nbp_api_addr = f'https://api.nbp.pl/api/exchangerates/rates/a/{currency}'
        for _ in range(7):
            self.date_value -= timedelta(days=1)
            nbp_api_addr += f'/{self.date_value}'

            try:
                req = requests.get(nbp_api_addr)
            except requests.exceptions.RequestException:
                self.err = {
                    'message': '502 Bad Gateway',
                    'error': 'The server got an invalid response while working as ' \
                        'a gateway to get the response needed to handle the request.'}, 500
                return None

            if req.status_code == 200:
                break
            nbp_api_addr = nbp_api_addr.rsplit('/', 1)[0]

        if req.status_code != 200:
            self.err = {
                'message': '500 Internal Server Error',
                'error': 'Failed to find data.'}, 500
            return None

        try:
            msg = json.loads(req.text)
        except json.decoder.JSONDecodeError:
            self.err = {
                'message': '500 Internal Server Error',
                'error': 'Failed to load data.'}, 500
            return None

        try:
            msg = {
                'message': 'Found exchange rates',
                'currency': f'{currency.upper()}',
                'searchedDate:': f'{date_string}',
                'effectiveDate': f'{msg["rates"][0]["effectiveDate"]}',
                'exchangeRate': f'{msg["rates"][0]["mid"]}'}
        except KeyError:
            self.err = {
                'message': '500 Internal Server Error',
                'error': 'Failed to format data.'}, 500
            return None

        return msg


    def get(self, currency, date_string):
        self.err = None
        self.__validate_input(currency, date_string)
        if self.err:
            return self.err

        msg = self.__get_searched_data(currency, date_string)
        if self.err:
            return self.err

        return msg, 200

def get_currencies_codes():
    table_a_addr = f'https://api.nbp.pl/api/exchangerates/tables/a'
    req = requests.get(table_a_addr)

    if req.status_code != 200:
        return None

    try:
        table_a = json.loads(req.text)
    except json.decoder.JSONDecodeError:
        app_logger.error('Couldn\'t load json - table A.')
        return None

    currencies = table_a[0]['rates']
    currencies_codes = set()

    for currency in currencies:
        currencies_codes.add(currency['code'])

    return tuple(currencies_codes)

def create_app():
    currencies_codes = get_currencies_codes()
    if not currencies_codes:
        app_logger.error('Couldn\'t create currencies code list for table A.')
        return None
    app = Flask(__name__)
    api = Api(app)
    api.add_resource(ExchangeRate, '/prevday/exchangerate/<string:currency>/<string:date_string>',
                     resource_class_kwargs={'currencies_codes': currencies_codes})
    return app

if __name__ == '__main__':
    wsgi_logger = logging.getLogger('wsgi')
    wsgi_formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')

    wsgi_file_handler = logging.FileHandler('nbp_exchange_rate.log')
    wsgi_file_handler.setFormatter(wsgi_formatter)

    wsgi_logger.addHandler(wsgi_file_handler)

    app_logger = logging.getLogger('app')
    app_formatter = logging.Formatter('%(levelname)s:%(name)s:%(asctime)s:%(message)s')

    app_file_handler = logging.FileHandler('nbp_exchange_rate.log')
    app_file_handler.setFormatter(app_formatter)

    app_stream_handler = logging.StreamHandler()
    app_stream_handler.setFormatter(app_formatter)

    app_logger.addHandler(app_file_handler)
    app_logger.addHandler(app_stream_handler)

    app = create_app()
    if not app:
        sys.exit(1)

    app_logged = TransLogger(app, setup_console_handler=False)
    serve(app_logged, host='0.0.0.0', port='5000')

    sys.exit(0)
