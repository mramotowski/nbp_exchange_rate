import unittest
from nbp_exchange_rate import create_app

def template_test(self, currency, date_string, status_code, expected_response):
    response = self.client.get(f'/prevday/exchangerate/{currency}/{date_string}')
    self.assertEqual(response.status_code, status_code)
    self.assertDictEqual(response.get_json(), expected_response)

class TestExchangeRate(unittest.TestCase):
    def setUp(self):
        app = create_app()
        self.client = app.test_client()

    def test_wrong_currency(self):
        currency = 'UDS'
        date_string = '2022-01-11'
        status_code = 400
        expected_response = {
            'message': '400 Bad Request',
            'error': 'Incorrect currency.'}
        template_test(self, currency, date_string, status_code, expected_response)

    def test_date_format(self):
        currency = 'USD'
        expected_response = {
            'message': '400 Bad Request',
            'error': 'Incorrect date string format. It should be YYYY-MM-DD.'}
        status_code = 400
        dates_to_test = ['2022 01 01', '2010.05.26']
        for date_string in dates_to_test:
            with self.subTest(date=date_string):
                template_test(self, currency, date_string, status_code, expected_response)

    def test_date_not_in_range(self):
        currency = 'USD'
        expected_response = {
            'message': '400 Bad Request',
            'error': 'Incorrect date. Correct date is between 2002-01-03 and present.'}
        status_code = 400

        dates_to_test = ['3210-01-13', '1926-05-26']
        for date_string in dates_to_test:
            with self.subTest(date=date_string):
                template_test(self, currency, date_string, status_code, expected_response)

    def test_day_after_wroking_day(self):
        currency = 'USD'
        date_string = '2022-01-13'
        expected_response = {
            'message': 'Found exchange rates',
            'currency': 'USD',
            'searchedDate:': '2022-01-13',
            'effectiveDate': '2022-01-12',
            'exchangeRate': '3.9879'}
        status_code = 200
        template_test(self, currency, date_string, status_code, expected_response)

    def test_day_after_free_day(self):
        currency = 'USD'
        date_string = '2022-01-10'
        expected_response = {
            'message': 'Found exchange rates',
            'currency': 'USD',
            'searchedDate:': '2022-01-10',
            'effectiveDate': '2022-01-07',
            'exchangeRate': '4.0279'}
        status_code = 200
        template_test(self, currency, date_string, status_code, expected_response)

if __name__ == "__main__":
    unittest.main()
