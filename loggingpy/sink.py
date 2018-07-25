import requests
import multiprocessing
import logging
import time
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


class BatchedHttpSink(logging.Handler):
    """
    Sends messages in batches using multithreading. Order of uploads is not deterministic. Make sure to include a time
    stamp into this message.
    """
    def __init__(self, endpoint_uri: str, batch_size_limit: int = 10, send_anyway_interval: int = 1):
        logging.Handler.__init__(self)
        self.endpoint_uri = endpoint_uri

        self.batch_size_limit = batch_size_limit
        self.send_anyway_interval = send_anyway_interval
        self.queue = multiprocessing.Queue(-1)

        self.current_time = time.time()
        self.queue_size = 0
        self.setFormatter(JsonFormatter())

    def send(self, s):
        self.queue.put_nowait(s)
        self.queue_size += 1

    def emit(self, record):
        try:
            log_entry = self.format(record)
            self.send(log_entry)

            self.process_queue()
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            self.handleError(record)

    def process_queue(self, flush_queue=False):

        pool = []

        while self.queue_size > self.batch_size_limit \
                or self.current_time > time.time() + self.send_anyway_interval \
                or flush_queue:
            batch = []
            for i in range(0, self.batch_size_limit):
                try:
                    m = self.queue.get_nowait()
                    batch.append(m)
                    self.queue_size -= 1
                except Exception as e:
                    break
                finally:
                    self.current_time = time.time()

            if len(batch) == 0:
                break

            for b in batch:
                p = multiprocessing.Process(target=post_request, args=((self.endpoint_uri, b),))
                p.start()
                pool.append(p)

            for p in pool:
                p.join()

    def flush(self):
        self.process_queue(flush_queue=True)

    def close(self):
        self.flush()
        logging.Handler.close(self)


class BundlingHttpSink(logging.Handler):
    """
    Sends messages by bundling multiple messages into one request.
    Adjusted version from: https://github.com/logzio/logzio-python-handler/tree/master/logzio
    """
    def __init__(self,
                 url,
                 logs_drain_timeout=3,
                 debug=False):

        self.http_sender = HttpSender(
            url=url,
            logs_drain_timeout=logs_drain_timeout,
            debug=debug)
        logging.Handler.__init__(self)

    def flush(self):
        self.http_sender.flush()

    def emit(self, record):
        log_entry = self.format(record)
        self.http_sender.append(log_entry)

