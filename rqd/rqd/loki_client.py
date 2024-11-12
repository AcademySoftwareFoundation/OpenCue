#! /usr/local/bin/python

#  Copyright Contributors to the OpenCue Project
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""Module for communicating with Loki"""

import datetime
import json
from typing import Dict, List
from urllib.parse import urlparse, urlencode
import urllib3


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
                hours_delta = DEFAULT_HOURS_DELTA):
        """
        constructor
        :param url:
        :param headers:
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
        # the days between start and end time
        self.hours_delta = hours_delta
        # the time range when searching context for one key line
        self.context_timedelta = int(CONTEXT_HOURS_DELTA * 3600 * 10 ** 9)

        self.__session = urllib3.PoolManager()
        self.__session.keep_alive = False

    def ready(self) -> bool:
        """
        Check whether Loki host is ready to accept traffic.
        Ref: https://grafana.com/docs/loki/v2.4/api/#get-ready
        :return:
        bool: True if Loki is ready, False otherwise.
        """
        try:
            response = self.__session.request(
                "GET",
                url="{}/ready".format(self.url),
                headers=self.headers
            )
            return bool(response.status == 200)
        # pylint: disable=bare-except
        except:
            return False

    def labels(self,
               start: datetime.datetime = None,
               end: datetime.datetime = None,
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
            if end is not type(datetime.datetime):
                return False, {
                    'message':
                        f'Incorrect end type {type(end)}, should be type {datetime.datetime}.'}
            # Convert to int, or will be scientific notation, which will result in request exception
            params['end'] = int(end.timestamp() * 10 ** 9)
        else:
            params['end'] = int(datetime.datetime.now().timestamp() * 10 ** 9)

        if start:
            if not isinstance(start, datetime.datetime):
                return False, {
                    'message':
                        f'Incorrect end type {type(start)}, should be type {datetime.datetime}.'}
            # Convert to int, or will be scientific notation, which will result in request exception
            params['start'] = int(start.timestamp() * 10 ** 9)
        else:
            params['start'] = int((datetime.datetime.fromtimestamp(params['end'] / 10 ** 9)
                                   - datetime.timedelta(hours=self.hours_delta)).timestamp()
                                  * 10 ** 9)

        enc_query = urlencode(params)
        target_url = '{}/loki/api/v1/labels?{}'.format(self.url, enc_query)

        try:
            response = self.__session.request(
                "GET",
                url=target_url,
                headers=self.headers
            )
            return bool(response.status == 200), response.json()
        except Exception as ex:
            return False, {'message': repr(ex)}

    def label_values(self,
                     label: str,
                     start: datetime.datetime = None,
                     end: datetime.datetime = None,
                     params : dict = None) -> tuple:
        """
        Get the list of known values for a given label within a given time span and
        corresponding values.
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
                return False, {'message':
                                   f'Incorrect label type {type(label)}, should be type {str}.'}
        else:
            return False, {'message':'Param label can not be empty.'}

        if end:
            if not isinstance(end, datetime.datetime):
                return False, {
                    'message':
                        f'Incorrect end type {type(end)}, should be type {datetime.datetime}.'}
            # Convert to int, or will be scientific notation, which will result in request exception
            params['end'] = int(end.timestamp() * 10 ** 9)
        else:
            params['end'] = int(datetime.datetime.now().timestamp() * 10 ** 9)

        if start:
            if not isinstance(start, datetime.datetime):
                return False, {
                    'message':
                        f'Incorrect start type {type(start)}, should be type {datetime.datetime}.'}
            # Convert to int, or will be scientific notation, which will result in request exception
            params['start'] = int(start.timestamp() * 10 ** 9)
        else:
            params['start'] = int(
                (datetime.datetime.fromtimestamp(params['end'] / 10 ** 9)
                 - datetime.timedelta(hours=self.hours_delta)).timestamp() * 10 ** 9)

        enc_query = urlencode(params)
        target_url = '{}/loki/api/v1/label/{}/values?{}'.format(self.url, label, enc_query)

        try:
            response = self.__session.request(
                "GET",
                url=target_url,
                headers=self.headers
            )
            return bool(response.status == 200), response.json()
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
                return False, {'message':
                                   f'Incorrect query type {type(query)}, should be type {str}.'}
            params['query'] = query
        else:
            return False, {'message':'Param query can not be empty.'}

        if limit:
            params['limit'] = limit
        else:
            return False, {'message': 'The value of limit is not correct.'}

        if time:
            if not isinstance(time, datetime.datetime):
                return False, {
                    'message':
                        f'Incorrect start type {type(time)}, should be type {datetime.datetime}.'}
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
            response = self.__session.request(
                "GET",
                url=target_url,
                headers=self.headers
            )
            return bool(response.status == 200), response.json()
        except Exception as ex:
            return False, {'message': repr(ex)}

    def query_range(self,
                    query: str,
                    limit: int = 100,
                    start: datetime.datetime = None,
                    end: datetime.datetime = None,
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
                return False, {'message':
                                   f'Incorrect query type {type(query)}, should be type {str}.'}
            params['query'] = query
        else:
            return False, {'message': 'Param query can not be empty.'}

        if end:
            if not isinstance(end, datetime.datetime):
                return False, {
                    'message':
                        f'Incorrect start type {type(start)}, should be type {datetime.datetime}.'}
            # Convert to int, or will be scientific notation, which will result in request exception
            params['end'] = int(end.timestamp() * 10 ** 9)
        else:
            params['end'] = int(datetime.datetime.now().timestamp() * 10 ** 9)

        if start:
            if not isinstance(start, datetime.datetime):
                return False, {
                    'message':
                        f'Incorrect start type {type(start)}, should be type {datetime.datetime}.'}
            # Convert to int, or will be scientific notation, which will result in request exception
            params['start'] = int(start.timestamp() * 10 ** 9)
        else:
            params['start'] = int((datetime.datetime.fromtimestamp(params['end'] / 10 ** 9)
                                   - datetime.timedelta(hours=self.hours_delta)).timestamp()
                                  * 10 ** 9)

        if limit:
            params['limit'] = limit
        else:
            return False, {'message': 'The value of limit is not correct.'}

        if direction not in SUPPORTED_DIRECTION:
            return False, {'message': 'Invalid direction value: {}.'.format(direction)}
        params['direction'] = direction

        enc_query = urlencode(params)
        target_url = f'{self.url}/loki/api/v1/query_range?{enc_query}'
        try:
            response = self.__session.request(
                "GET",
                url=target_url,
                headers=self.headers
            )
            if response.status == 200:
                return True, response.json()
            return False, response.data
        except Exception as ex:
            return False, {'message': repr(ex)}

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
            response = self.__session.request(
                "POST",
                url=target_url,
                body=payload_json,
                headers=headers
            )
            return bool(response.status == 204), response.reason
        except Exception as ex:
            return False, {'message': repr(ex)}
