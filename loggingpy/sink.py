import requests
import logging
import signal
from loggingpy.log import JsonFormatter
import logging.handlers

from .sender import HttpSender


class SimpleHttpSink(logging.Handler):
    """
    Sends every log message in series one-by-one.
    """

    def __init__(self, endpoint_uri: str):
        logging.Handler.__init__(self)
        self.endpoint_uri = endpoint_uri
        self.setFormatter(JsonFormatter())

    def emit(self, record):
        log_entry = self.format(record)
        try:
            return requests.post(self.endpoint_uri, log_entry, headers={"Content-type": "application/json"}).content
        except Exception as ex:  # after the post retries, all bets are off
            print(ex)


def post_request(info):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    endpoint_uri, log_entry = info[0], info[1]
    try:
        return requests.post(endpoint_uri, log_entry, headers={"Content-type": "application/json"}).content
    except Exception as ex:  # after the post retries, all bets are off
        print(ex)


class BundlingHttpSink(logging.Handler):
    """
    Sends messages by bundling multiple messages into one request.
    Adjusted version from: https://github.com/logzio/logzio-python-handler/tree/master/logzio
    """
    def __init__(self,
                 app_name,
                 url,
                 logs_drain_timeout=3,
                 debug=False):

        self.app_name = app_name

        self.http_sender = HttpSender(
            url=url,
            logs_drain_timeout=logs_drain_timeout,
            debug=debug)
        logging.Handler.__init__(self)

    def flush(self):
        self.http_sender.flush()

    def emit(self, record):
        record.app_name = self.app_name
        log_entry = self.format(record)
        self.http_sender.append(log_entry)

