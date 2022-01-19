import unittest
import nbp_exchange_rate

def template_test(app, data, status_code, expected_response):
    response = app.client.get('/', query_string=data)
    app.assertEqual(response.status_code, status_code)
    app.assertDictEqual(response.get_json(), expected_response)

class TestExchangeRate(unittest.TestCase):
    def setUp(self):
        self.app = nbp_exchange_rate.app
        self.client = self.app.test_client()

    def test_wrong_currency(self):
        data = {
            'currency': 'UDS',
            'date': '2022-01-11'}
        status_code = 400
        expected_response = {
            'message': '400 Bad Request',
            'error': 'Incorrect currency.'}
        template_test(self, data, status_code, expected_response)

    def test_date_format(self):
        data = {
            'currency': 'USD',
            'date': ''}
        expected_response = {
            'message': '400 bad request',
            'error': 'Incorrect date string format. It should be YYYY-MM-DD.'}
        status_code = 400
        dates_to_test = ['2010/04/13', '2010.05.26']
        for date in dates_to_test:
            with self.subTest(date=date):
                data['date'] = date
                template_test(self, data, status_code, expected_response)

    def test_date_not_in_range(self):
        data = {
            'currency': 'USD',
            'date': ''}
        expected_response = {
            'message': '400 bad request',
            'error': 'Incorrect date. Correct date is between 2002-01-03 and present.'}
        status_code = 400

        dates_to_test = ['3210-01-13', '1926-05-26']
        for date in dates_to_test:
            with self.subTest(date=date):
                data['date'] = date
                template_test(self, data, status_code, expected_response)

    def test_day_after_wroking_day(self):
        data = {
            'currency': 'USD',
            'date': '2022-01-13'}
        expected_response = {'message': '{\'table\': \'A\', \'currency\': \'dolar ameryka\u0144ski\', \'code\': \'USD\', \'rates\': [{\'no\': \'007/A/NBP/2022\', \'effectiveDate\': \'2022-01-12\', \'mid\': 3.9879}]}'}
        status_code = 200
        template_test(self, data, status_code, expected_response)

    def test_day_after_free_day(self):
        data = {
            'currency': 'USD',
            'date': '2022-01-11'}
        expected_response = {"message": "{'table': 'A', 'currency': 'dolar ameryka\u0144ski', 'code': 'USD', 'rates': [{'no': '005/A/NBP/2022', 'effectiveDate': '2022-01-10', 'mid': 4.0064}]}"}
        status_code = 200
        template_test(self, data, status_code, expected_response)

if __name__ == "__main__":
    unittest.main()
