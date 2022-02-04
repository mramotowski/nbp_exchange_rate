from datetime import date, datetime, timedelta
import json
import logging
import requests
from flask_restful import Resource

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

    @staticmethod
    def __get_searched_data(currency, date_string):
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
