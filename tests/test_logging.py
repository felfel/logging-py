from loggingpy.log import Logger
import logging.handlers
from loggingpy.log import JsonFormatter


class AssertionSink(logging.Handler):
    test_method = None
    test_count = 0

    def __init__(self):
        logging.Handler.__init__(self)
        self.setFormatter(JsonFormatter())

    def emit(self, record):
        if self.test_method is None:
            assert False

        formatted_string = self.format(record)
        self.test_count += self.test_method(self.test_count, record, formatted_string)


test_sink = AssertionSink()


def test_data_but_no_payload_type():

    Logger.with_sink(test_sink)
    test_logger = Logger(test_data_but_no_payload_type.__name__)

    def test(record_count, record: logging.LogRecord, formatted_string: str):
        if record_count == 0:
            assert record.msg == '1'  # this is the first message
            assert 'missing_payload_type' in formatted_string
        if record_count == 1:
            assert record.msg == "The previous message lacks a payload type, but appends payload. Don't be lazy, add a payload type."  # this is the second message because of the first message

        return 1

    test_sink.test_method = test
    test_logger.debug(message='1', data={
        'stuff': 1
    })
''