from loggingpy.log import LogEntry, LogEntryParser, LogLevel


class TestLoggingExceptions:

    error_message = 'Outch'

    def setup(self):
        pass

    def teardown(self):
        pass

    def test_exception_information_should_be_present(self):
        dto = TestLoggingExceptions.create_dto()
        assert dto['exception'] is not None
        assert dto['exception']['error_message'] is TestLoggingExceptions.error_message
        assert dto['exception']['exception_type'] == 'ZeroDivisionError'
        assert dto['exception']['stack_trace'] is not None and dto['exception']['stack_trace'] is not ''
        assert dto['exception']['exception_hash'] is not None and dto['exception']['exception_hash'] is not ''

    def test_same_exception_with_different_message_should_still_result_in_same_hash(self):
        dto1 = TestLoggingExceptions.create_dto(message='aaa')
        dto2 = TestLoggingExceptions.create_dto(message='bbb')

        assert dto1['exception']['error_message'] == 'aaa'
        assert dto2['exception']['error_message'] == 'bbb'

        assert dto1['exception']['exception_hash'] == dto2['exception']['exception_hash']

    def test_same_exception_type_can_result_in_different_hash(self):
        dto1 = TestLoggingExceptions.create_dto(True)
        dto2 = TestLoggingExceptions.create_dto(False)

        assert dto1['exception']['exception_hash'] != dto2['exception']['exception_hash']

    # helper methods
    @staticmethod
    def create_dto(alternate_stack_trace: bool=False, message: str=error_message):
        le = LogEntry(exception=TestLoggingExceptions.create_exception(alternate_stack_trace, message), log_level=LogLevel.Info, context='context', payload_type='type')
        return LogEntryParser.parse_log_entry(le)

    @staticmethod
    def create_exception(alternate_stack_trace: bool, message: str):
        if alternate_stack_trace:
            try:
                raise ZeroDivisionError(message)
            except ZeroDivisionError as e:
                return e

        try:
            raise ZeroDivisionError(message)
        except ZeroDivisionError as e:
            return e
