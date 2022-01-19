import requests
from flask import Flask
from flask_restful import Resource, Api
from flask_restful import reqparse
from datetime import date, datetime, timedelta
import json

app = Flask(__name__)
api = Api(app)

parser = reqparse.RequestParser()
parser.add_argument('currency', type=str, help='Foreign currency of obtained income')
parser.add_argument('date', type=str, help='Day of obtaining the income')

class ExchangeRate(Resource):
    def get(self):
        args = parser.parse_args()
        nbpApiAddress = f'https://api.nbp.pl/api/exchangerates/rates/a/{args.currency}'

        request = requests.get(nbpApiAddress)
        if request.status_code > 299:
            return {'message': '400 Bad Request', 'error': 'Incorrect currency.'}, 400

        try:
            dateValue = date.fromisoformat(args.date)
        except ValueError:
            return {'message': '400 bad request', 'error': 'Incorrect date string format. It should be YYYY-MM-DD.'}, 400

        dateValue -= timedelta(days=1)
        if dateValue > datetime.now().date() or date.fromisoformat('2002-01-02') > dateValue:
            return {'message': '400 bad request', 'error': 'Incorrect date. Correct date is between 2002-01-03 and present.'}, 400

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

api.add_resource(ExchangeRate, '/')

if __name__ == '__main__':
    app.run(host='0.0.0.0')
