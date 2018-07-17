import requests
import multiprocessing
import logging
import time


class HttpSink(logging.Handler):

    def __init__(self, endpoint_uri: str):
        logging.Handler.__init__(self)
        self.endpoint_uri = endpoint_uri

    def emit(self, record):
        log_entry = self.format(record)

        return requests.post(self.endpoint_uri, log_entry, headers={"Content-type": "application/json"}).content


def post_request(info):
        endpoint_uri, log_entry = info[0], info[1]
        return requests.post(endpoint_uri, log_entry, headers={"Content-type": "application/json"}).content


class BatchedHttpSink(logging.Handler):
    def __init__(self, endpoint_uri: str, batch_size_limit: int, send_anyway_interval: int):
        logging.Handler.__init__(self)
        self.endpoint_uri = endpoint_uri

        self.batch_size_limit = batch_size_limit
        self.send_anyway_interval = send_anyway_interval
        self.queue = multiprocessing.Queue(-1)
        self.pool = multiprocessing.Pool(50 if batch_size_limit > 50 else batch_size_limit)
        self.current_time = time.time()
        self.queue_size = 0

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

    def process_queue(self):
        while self.queue_size > self.batch_size_limit or self.current_time > time.time() + self.send_anyway_interval:
            batch = []
            for i in range(0, self.batch_size_limit):
                try:
                    m = self.queue.get_nowait()
                    batch.append(m)
                    self.queue_size -= 1
                except Exception as e:
                    break

            results = self.pool.map_async(post_request, [(self.endpoint_uri, b) for b in batch])
            self.current_time = time.time()
            results.get()

    def flush(self):
        self.process_queue()

    def close(self):
        self.process_queue()
        self.pool.terminate()
        self.pool.join()
        logging.Handler.close(self)
