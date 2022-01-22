import requests
from flask import Flask
from flask_restful import Resource, Api
from flask_restful import reqparse
from datetime import date, datetime, timedelta
import json

def get_currencies_codes():
    table_a_addr = f'https://api.nbp.pl/api/exchangerates/tables/a'
    request = requests.get(table_a_addr)
    table_a = json.loads(request.text)
    currencies = table_a[0]['rates']
    currencies_codes = set()

    for currency in currencies:
        currencies_codes.add(currency['code'])

    return tuple(currencies_codes)

app = Flask(__name__)
api = Api(app)

parser = reqparse.RequestParser()
parser.add_argument('currency', type=str, help='Foreign currency of obtained income')
parser.add_argument('date', type=str, help='Day of obtaining the income')

class ExchangeRate(Resource):
    def __init__(self, currencies_codes):
        self.currencies_codes = currencies_codes

    def get(self):
        args = parser.parse_args()

        if args.currency.upper() not in self.currencies_codes:
            return {'message': '400 Bad Request', 'error': 'Incorrect currency.'}, 400

        try:
            dateValue = date.fromisoformat(args.date)
        except ValueError:
            return {'message': '400 bad request', 'error': 'Incorrect date string format. It should be YYYY-MM-DD.'}, 400

        dateValue -= timedelta(days=1)
        if dateValue > datetime.now().date() or date.fromisoformat('2002-01-02') > dateValue:
            return {'message': '400 bad request', 'error': 'Incorrect date. Correct date is between 2002-01-03 and present.'}, 400

        nbpApiAddress = f'https://api.nbp.pl/api/exchangerates/rates/a/{args.currency}'
        for dayBefore in range(7):
            nbpApiAddress += f'/{dateValue}'
            request = requests.get(nbpApiAddress)
            if request.status_code == 200:
                break
            nbpApiAddress = nbpApiAddress.rsplit('/', 1)[0]
            dateValue -= timedelta(days=1)

        if request.status_code != 200:
            return {'message': '404 Not Found', 'error': 'The server can not find the requested resource.'}, 404

        message = json.loads(request.text)
        return {'message': f'{message}'}, 200


if __name__ == '__main__':
    currencies_codes = get_currencies_codes()
    api.add_resource(ExchangeRate, '/',
                     resource_class_kwargs={'currencies_codes': currencies_codes})
    app.run(host='0.0.0.0')
