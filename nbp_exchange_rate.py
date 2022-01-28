import requests
from flask import Flask
from flask_restful import Resource, Api
from flask_restful import reqparse
from datetime import date, datetime, timedelta
from waitress import serve
from paste.translogger import TransLogger
import json
import sys

class ExchangeRate(Resource):
    def __init__(self, currencies_codes):
        self.currencies_codes = currencies_codes

    def get(self, currency, date_string):
        if currency.upper() not in self.currencies_codes:
            return {'message': '400 Bad Request', 'error': 'Incorrect currency.'}, 400

        try:
            dateValue = date.fromisoformat(date_string)
        except ValueError:
            return {'message': '400 Bad Request', 'error': 'Incorrect date string format. It should be YYYY-MM-DD.'}, 400

        if dateValue > datetime.now().date() or date.fromisoformat('2002-01-02') > dateValue:
            return {'message': '400 Bad Request', 'error': 'Incorrect date. Correct date is between 2002-01-03 and present.'}, 400

        nbpApiAddress = f'https://api.nbp.pl/api/exchangerates/rates/a/{currency}'
        for dayBefore in range(7):
            dateValue -= timedelta(days=1)
            nbpApiAddress += f'/{dateValue}'
            request = requests.get(nbpApiAddress)
            if request.status_code == 200:
                break
            nbpApiAddress = nbpApiAddress.rsplit('/', 1)[0]

        if request.status_code != 200:
            return {'message': '404 Not Found', 'error': 'The server can not find the requested resource.'}, 404

        try:
            message = json.loads(request.text)
        except json.decoder.JSONDecodeError:
            return {'message': '500 Internal Server Error', 'error': 'Failed to load data.'}, 500

        try:
            message = f'Exchange rate of {currency.upper()} to PLN for first business day preceding {date_string} is from {message["rates"][0]["effectiveDate"]} and is {message["rates"][0]["mid"]}'
        except KeyError:
            return {'message': '500 Internal Server Error', 'error': 'Failed to format data.'}, 500

        return {'message': f'{message}'}, 200

def get_currencies_codes():
    table_a_addr = f'https://api.nbp.pl/api/exchangerates/tables/a'
    request = requests.get(table_a_addr)

    if request.status_code != 200:
        return

    try:
        table_a = json.loads(request.text)
    except json.decoder.JSONDecodeError:
        return

    currencies = table_a[0]['rates']
    currencies_codes = set()

    for currency in currencies:
        currencies_codes.add(currency['code'])

    return tuple(currencies_codes)

def create_app():
    currencies_codes = get_currencies_codes()
    if not currencies_codes:
        return
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
