from urllib.parse import urlparse, urlencode
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import datetime
import json
from typing import Dict, List

# Support Loki version:2.4.2
MAX_REQUEST_RETRIES = 3
RETRY_BACKOFF_FACTOR =1
RETRY_ON_STATUS = [408, 429, 500, 502, 503, 504]
SUPPORTED_DIRECTION = ["backward", "forward"]
# the duration before end time when get context
CONTEXT_HOURS_DELTA = 1
DEFAULT_HOURS_DELTA = 2 * 24


class LokiClient(object):
    """
    Loki client for Python to communicate with Loki server.
    Ref: https://grafana.com/docs/loki/v2.4/api/
    """
    def __init__(self,
                url: str = "http://127.0.0.1:3100",
                headers: dict = None,
                disable_ssl: bool = True,
                retry: Retry = None,
                hours_delta = DEFAULT_HOURS_DELTA):
        """
        constructor
        :param url:
        :param headers:
        :param disable_ssl:
        :param retry:
        :param hours_delta:
        :return:
        """
        if url is None:
            raise TypeError("Url can not be empty!")

        self.headers = headers
        self.url = url
        self.loki_host = urlparse(self.url).netloc
        self._all_metrics = None
        self.ssl_verification = not disable_ssl
        # the days between start and end time
        self.hours_delta = hours_delta
        # the time range when searching context for one key line
        self.context_timedelta = int(CONTEXT_HOURS_DELTA * 3600 * 10 ** 9)

        if retry is None:
            retry = Retry(total=MAX_REQUEST_RETRIES, backoff_factor=RETRY_BACKOFF_FACTOR, status_forcelist=RETRY_ON_STATUS)

        self.__session = requests.Session()
        self.__session.mount(self.url, HTTPAdapter(max_retries=retry))
        self.__session.keep_alive = False

    def ready(self) -> bool:
        """
        Check whether Loki host is ready to accept traffic.
        Ref: https://grafana.com/docs/loki/v2.4/api/#get-ready
        :return:
        bool: True if Loki is ready, False otherwise.
        """
        try:
            response = self.__session.get(
                url="{}/ready".format(self.url),
                verify=self.ssl_verification,
                headers=self.headers
            )
            return response.ok
        except Exception as ex:
            return False

    def labels(self,
               start: datetime = None,
               end: datetime = None,
               params: dict = None) -> tuple:
        """
        Get the list of known labels within a given time span, corresponding labels.
        Ref: GET /loki/api/v1/labels
        :param start:
        :param end:
        :param params:
        :return:
        """
        params = params or {}

        if end:
            if not isinstance(end, datetime):
                return False, {'message': 'Incorrect end type {}, should be type {}.'.format(type(end), datetime)}
            # Convert to int, or will be scientific notation, which will result in request exception
            params['end'] = int(end.timestamp() * 10 ** 9)
        else:
            params['end'] = int(datetime.datetime.now().timestamp() * 10 ** 9)

        if start:
            if not isinstance(start, datetime):
                return False, {'message': 'Incorrect start type {}, should be type {}.'.format(type(start), datetime)}
            # Convert to int, or will be scientific notation, which will result in request exception
            params['start'] = int(start.timestamp() * 10 ** 9)
        else:
            params['start'] = int((datetime.datetime.fromtimestamp(params['end'] / 10 ** 9) - datetime.timedelta(hours=self.hours_delta)).timestamp() * 10 ** 9)

        enc_query = urlencode(params)
        target_url = '{}/loki/api/v1/labels?{}'.format(self.url, enc_query)

        try:
            response = self.__session.get(
                url=target_url,
                verify=self.ssl_verification,
                headers=self.headers
            )
            return response.ok, response.json()
        except Exception as ex:
            return False, {'message': repr(ex)}

    def label_values(self,
                     label: str,
                     start: datetime = None,
                     end: datetime = None,
                     params : dict = None) -> tuple:
        """
        Get the list of known values for a given label within a given time span, corresponding values.
        Ref: GET /loki/api/v1/label/<name>/values
        :param label:
        :param start:
        :param end:
        :param params:
        :return:
        """
        params = params or {}

        if label:
            if not isinstance(label, str):
                return False, {'message': 'Incorrect label type {}, should be type {}.'.format(type(label), str)}
        else:
            return False, {'message':'Param label can not be empty.'}

        if end:
            if not isinstance(end, datetime):
                return False, {'message': 'Incorrect end type {}, should be type {}.'.format(type(end), datetime)}
            # Convert to int, or will be scientific notation, which will result in request exception
            params['end'] = int(end.timestamp() * 10 ** 9)
        else:
            params['end'] = int(datetime.datetime.now().timestamp() * 10 ** 9)

        if start:
            if not isinstance(start, datetime):
                return False, {'message': 'Incorrect start type {}, should be type {}.'.format(type(start), datetime)}
            # Convert to int, or will be scientific notation, which will result in request exception
            params['start'] = int(start.timestamp() * 10 ** 9)
        else:
            params['start'] = int((datetime.datetime.fromtimestamp(params['end'] / 10 ** 9) - datetime.timedelta(
                hours=self.hours_delta)).timestamp() * 10 ** 9)

        enc_query = urlencode(params)
        target_url = '{}/loki/api/v1/label/{}/values?{}'.format(self.url, label, enc_query)

        try:
            response = self.__session.get(
                url=target_url,
                verify=self.ssl_verification,
                headers=self.headers
            )
            return response.ok, response.json()
        except Exception as ex:
            return False, {'message': repr(ex)}

    def query(self,
              query: str,
              limit: int = 100,
              time: datetime = None,
              direction: str = SUPPORTED_DIRECTION[0],
              params: dict = None) -> tuple:
        """
        Query logs from Loki, corresponding query.
        Ref: GET /loki/api/v1/query
        :param query:
        :param limit:
        :param time:
        :param direction:
        :param params:
        :return:
        """
        params = params or {}

        if query:
            if not isinstance(query, str):
                return False, {'message': 'Incorrect query type {}, should be type {}.'.format(type(query), str)}
            params['query'] = query
        else:
            return False, {'message':'Param query can not be empty.'}

        if limit:
            params['limit'] = limit
        else:
            return False, {'message': 'The value of limit is not correct.'}

        if time:
            if not isinstance(time, datetime):
                return False, {'message': 'Incorrect time type {}, should be type {}.'.format(type(time), datetime)}
            # Convert to int, or will be scientific notation, which will result in request exception
            params['time'] = int(time.timestamp() * 10 ** 9)
        else:
            params['time'] = int(datetime.datetime.now().timestamp() * 10 ** 9)

        if direction not in SUPPORTED_DIRECTION:
            return False, {'message': 'Invalid direction value: {}.'.format(direction)}
        params['direction'] = direction

        enc_query = urlencode(params)
        target_url = '{}/loki/api/v1/query?{}'.format(self.url, enc_query)

        try:
            response = self.__session.get(
                url=target_url,
                verify=self.ssl_verification,
                headers=self.headers
            )
            return response.ok, response.json()
        except Exception as ex:
            return False, {'message': repr(ex)}

    def query_range(self,
                    query: str,
                    limit: int = 100,
                    start: datetime = None,
                    end: datetime = None,
                    direction: str = SUPPORTED_DIRECTION[0],
                    params: dict = None) -> tuple:
        """
        Query logs from Loki, corresponding query_range.
        Ref: GET /loki/api/v1/query_range
        :param query:
        :param limit:
        :param start:
        :param end:
        :param direction:
        :param params:
        :return:
        """
        params = params or {}
        if query:
            if not isinstance(query, str):
                return False, {'message': 'Incorrect query type {}, should be type {}.'.format(type(query), str)}
            params['query'] = query
        else:
            return False, {'message': 'Param query can not be empty.'}

        if end:
            if not isinstance(end, datetime):
                return False, {'message': 'Incorrect end type {}, should be type {}.'.format(type(end), datetime)}
            # Convert to int, or will be scientific notation, which will result in request exception
            params['end'] = int(end.timestamp() * 10 ** 9)
        else:
            params['end'] = int(datetime.datetime.now().timestamp() * 10 ** 9)

        if start:
            if not isinstance(start, datetime):
                return False, {'message': 'Incorrect start type {}, should be type {}.'.format(type(start), datetime)}
            # Convert to int, or will be scientific notation, which will result in request exception
            params['start'] = int(start.timestamp() * 10 ** 9)
        else:
            params['start'] = int((datetime.datetime.fromtimestamp(params['end'] / 10 ** 9) - datetime.timedelta(hours=self.hours_delta)).timestamp() * 10 ** 9)

        if limit:
            params['limit'] = limit
        else:
            return False, {'message': 'The value of limit is not correct.'}

        if direction not in SUPPORTED_DIRECTION:
            return False, {'message': 'Invalid direction value: {}.'.format(direction)}
        params['direction'] = direction

        enc_query = urlencode(params)
        target_url = '{}/loki/api/v1/query_range?{}'.format(self.url, enc_query)

        try:
            response = self.__session.get(
                url=target_url,
                verify=self.ssl_verification,
                headers=self.headers
            )
            return response.ok, response.json()
        except Exception as ex:
            return False, {'message': repr(ex)}

    def query_range_with_context(self,
                                 query: str,
                                 limit: int = 100,
                                 context_before: int = 5,
                                 context_after: int = 3,
                                 start: datetime = None,
                                 end: datetime = None,
                                 direction: str = SUPPORTED_DIRECTION[1],
                                 params: dict = None) -> tuple:
        """
        Query key logs from Loki with contexts.
        Ref: GET /loki/api/v1/query_range
        :param query:
        :param limit:
        :param context_before:
        :param context_after:
        :param start:
        :param end:
        :param direction:
        :param params:
        :return:
        """
        params = params or {}

        if query:
            if not isinstance(query, str):
                return False, {'message': 'Incorrect query type {}, should be type {}.'.format(type(query), str)}
            params['query'] = query
        else:
            return False, {'message': 'Param query can not be empty.'}

        if end:
            if not isinstance(end, datetime):
                return False, {'message': 'Incorrect end type {}, should be type {}.'.format(type(end), datetime)}
            # Convert to int, or will be scientific notation, which will result in request exception
            params['end'] = int(end.timestamp() * 10 ** 9)
        else:
            params['end'] = int(datetime.datetime.now().timestamp() * 10 ** 9)

        if start:
            if not isinstance(start, datetime):
                return False, {'message': 'Incorrect start type {}, should be type {}.'.format(type(start), datetime)}
            # Convert to int, or will be scientific notation, which will result in request exception
            params['start'] = int(start.timestamp() * 10 ** 9)
        else:
            params['start'] = int((datetime.datetime.fromtimestamp(params['end'] / 10 ** 9) - datetime.timedelta(
                hours=self.hours_delta)).timestamp() * 10 ** 9)

        if limit:
            params['limit'] = limit
        else:
            return False, {'message': 'The value of limit is not correct.'}

        if direction not in SUPPORTED_DIRECTION:
            return False, {'message': 'Invalid direction value: {}.'.format(direction)}
        params['direction'] = direction

        enc_query = urlencode(params)
        target_url = '{}/loki/api/v1/query_range?{}'.format(self.url, enc_query)

        try:
            response = self.__session.get(
                url=target_url,
                verify=self.ssl_verification,
                headers=self.headers
            )
        except Exception as ex:
            return False, {'message': repr(ex)}

        if not response.ok:
            return False, {'message': response.reason}

        key_log_result = response.json()

        if key_log_result['status'] != 'success':
            return False, {'message': 'Query from Loki unsuccessfully.'}

        context_results = []

        for result_item in key_log_result['data']['result']:
            labels = result_item['stream']
            file_name = result_item['stream']['filename']
            file_datas = []
            for value_item in result_item['values']:
                cur_ts = int(value_item[0])
                key_line = value_item[1].strip()

                start_ts = cur_ts - self.context_timedelta
                end_ts = cur_ts + self.context_timedelta

                lbs = [r'%s="%s"' % (i, labels[i]) for i in labels.keys()]
                q = ','.join(lbs)
                query = '{' + q + '}'

                # context before
                params_ctx_before = {
                    'query': query,
                    'limit': context_before,
                    'start': start_ts,
                    'end': cur_ts,
                    'direction': SUPPORTED_DIRECTION[0]
                }

                enc_query = urlencode(params_ctx_before)
                target_url = '{}/loki/api/v1/query_range?{}'.format(self.url, enc_query)

                try:
                    response = self.__session.get(
                        url=target_url,
                        verify=self.ssl_verification,
                        headers=self.headers
                    )
                    ctx_before = response.json()
                except Exception as ex:
                    return False, {'message': repr(ex)}

                # context after
                params_ctx_after = {
                    'query': query,
                    'limit': context_after + 1,
                    'start': cur_ts,
                    'end': end_ts,
                    'direction': SUPPORTED_DIRECTION[1]
                }

                enc_query = urlencode(params_ctx_after)
                target_url = '{}/loki/api/v1/query_range?{}'.format(self.url, enc_query)

                try:
                    response = self.__session.get(
                        url=target_url,
                        verify=self.ssl_verification,
                        headers=self.headers
                    )
                    ctx_after = response.json()
                except Exception as ex:
                    return False, {'message': repr(ex)}

                key_line_ctx = []
                for value_item in reversed(ctx_before['data']['result'][0]['values']):
                    key_line_ctx.append(value_item[1].strip())

                # context_after result including the key line
                for value_item in ctx_after['data']['result'][0]['values']:
                    key_line_ctx.append(value_item[1].strip())

                data_item = {
                    'key_line': key_line,
                    'context': key_line_ctx
                }

                file_datas.append(data_item)

            result_item = {
                'file_name': file_name,
                'datas': file_datas
            }

            context_results.append(result_item)

        return True, {'results': context_results}

    def query_context_by_timestamp(self,
                                   query: str,
                                   cur_ts: int,
                                   context_before: int = 5,
                                   context_after: int = 3,
                                   params: dict = None) -> tuple:
        """
        Query contexts by the given query and timestamp.
        Ref: GET /loki/api/v1/query_range
        :param query:
        :param cur_ts:
        :param context_before:
        :param context_after:
        :param params:
        :return:
        """
        params = params or {}

        if query:
            if not isinstance(query, str):
                return False, {'message': 'Incorrect query type {}, should be type {}.'.format(type(query), str)}
            params['query'] = query
        else:
            return False, {'message': 'Param query can not be empty.'}

        start_ts = cur_ts - self.context_timedelta
        end_ts = cur_ts + self.context_timedelta

        # context before
        params_ctx_before = {
            'query': query,
            'limit': context_before,
            'start': start_ts,
            'end': cur_ts,
            'direction': SUPPORTED_DIRECTION[0]
        }

        enc_query = urlencode(params_ctx_before)
        target_url = '{}/loki/api/v1/query_range?{}'.format(self.url, enc_query)

        try:
            response = self.__session.get(
                url=target_url,
                verify=self.ssl_verification,
                headers=self.headers
            )
            ctx_before = response.json()
        except Exception as ex:
            return False, {'message': repr(ex)}

        # context after
        params_ctx_after = {
            'query': query,
            'limit': context_after + 1,
            'start': cur_ts,
            'end': end_ts,
            'direction': SUPPORTED_DIRECTION[1]
        }

        enc_query = urlencode(params_ctx_after)
        target_url = '{}/loki/api/v1/query_range?{}'.format(self.url, enc_query)

        try:
            response = self.__session.get(
                url=target_url,
                verify=self.ssl_verification,
                headers=self.headers
            )
            ctx_after = response.json()
        except Exception as ex:
            return False, {'message': repr(ex)}

        key_line_ctx = []
        for value_item in reversed(ctx_before['data']['result'][0]['values']):
            key_line_ctx.append(value_item[1].strip())

        # context_after result including the key line
        for value_item in ctx_after['data']['result'][0]['values']:
            key_line_ctx.append(value_item[1].strip())

        data_item = {
            'key_line': ctx_after['data']['result'][0]['values'][0][1].strip(),
            'context': key_line_ctx
        }

        return True, data_item

    def post(self, labels: Dict[str, str], logs: List[str]) -> tuple:
        """
        Post logs to Loki, with given labels.
        Ref: POST /loki/api/v1/push
        :param labels:
        :param logs:
        :return:
        """
        headers = {
            'Content-type': 'application/json'
        }

        cur_ts = int(datetime.datetime.now().timestamp() * 10 ** 9)
        logs_ts = [[str(cur_ts), log] for log in logs]

        payload = {
            'streams': [
                {
                    'stream': labels,
                    'values': logs_ts
                }
            ]
        }

        payload_json = json.dumps(payload)
        target_url = '{}/loki/api/v1/push'.format(self.url)

        try:
            response = self.__session.post(
                url=target_url,
                verify=self.ssl_verification,
                data=payload_json,
                headers=headers
            )
            return response.ok, response.reason
        except Exception as ex:
            return False, {'message': repr(ex)}
