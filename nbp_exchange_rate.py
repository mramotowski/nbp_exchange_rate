from datetime import date, datetime, timedelta
import json
import sys
import requests
from flask import Flask
from flask_restful import Resource, Api
from paste.translogger import TransLogger
from waitress import serve

class ExchangeRate(Resource):
    def __init__(self, currencies_codes):
        self.currencies_codes = currencies_codes

    def get(self, currency, date_string):
        if currency.upper() not in self.currencies_codes:
            return {
                'message': '400 Bad Request',
                'error': 'Incorrect currency.'}, 400

        try:
            date_value = date.fromisoformat(date_string)
        except ValueError:
            return {
                'message': '400 Bad Request',
                'error': 'Incorrect date string format. It should be YYYY-MM-DD.'}, 400

        if date_value > datetime.now().date() or date.fromisoformat('2002-01-02') > date_value:
            return {
                'message': '400 Bad Request',
                'error': 'Incorrect date. Correct date is between 2002-01-03 and present.'}, 400

        nbp_api_addr = f'https://api.nbp.pl/api/exchangerates/rates/a/{currency}'
        for _ in range(7):
            date_value -= timedelta(days=1)
            nbp_api_addr += f'/{date_value}'
            req = requests.get(nbp_api_addr)
            if req.status_code == 200:
                break
            nbp_api_addr = nbp_api_addr.rsplit('/', 1)[0]

        if req.status_code != 200:
            return {
                'message': '404 Not Found',
                'error': 'The server can not find the requested resource.'}, 404

        try:
            msg = json.loads(req.text)
        except json.decoder.JSONDecodeError:
            return {'message': '500 Internal Server Error', 'error': 'Failed to load data.'}, 500

        try:
            msg = {
                'message': 'Found exchange rates',
                'currency': f'{currency.upper()}',
                'searchedDate:': f'{date_string}',
                'effectiveDate': f'{msg["rates"][0]["effectiveDate"]}',
                'exchangeRate': f'{msg["rates"][0]["mid"]}'}
        except KeyError:
            return {
                'message': '500 Internal Server Error',
                'error': 'Failed to format data.'}, 500

        return msg, 200

def get_currencies_codes():
    table_a_addr = f'https://api.nbp.pl/api/exchangerates/tables/a'
    req = requests.get(table_a_addr)

    if req.status_code != 200:
        return None

    try:
        table_a = json.loads(req.text)
    except json.decoder.JSONDecodeError:
        return None

    currencies = table_a[0]['rates']
    currencies_codes = set()

    for currency in currencies:
        currencies_codes.add(currency['code'])

    return tuple(currencies_codes)

def create_app():
    currencies_codes = get_currencies_codes()
    if not currencies_codes:
        return None
    app = Flask(__name__)
    api = Api(app)
    api.add_resource(ExchangeRate, '/prevday/exchangerate/<string:currency>/<string:date_string>',
                     resource_class_kwargs={'currencies_codes': currencies_codes})
    return app

if __name__ == '__main__':
    app = create_app()
    if not app:
        print('Couldn\'t create currencies code list for table A.')
        sys.exit(1)
    serve(TransLogger(app, setup_console_handler=False), host='0.0.0.0', port='5000')
    sys.exit(0)
