import logging
import requests


class HttpSink(logging.Handler):

    def __init__(self, endpoint_uri: str):
        logging.Handler.__init__(self)
        self.endpoint_uri = endpoint_uri

    def emit(self, record):
        log_entry = self.format(record)

        return requests.post(self.endpoint_uri, log_entry, headers={"Content-type": "application/json"}).content
