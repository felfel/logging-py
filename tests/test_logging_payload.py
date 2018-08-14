from loggingpy.log import LogEntry, LogEntryParser, LogLevel


class TestLoggingPayload:
    def setup(self):
        pass

    def teardown(self):
        pass

    def test_simple_string_should_still_be_json(self):
        le = LogEntry(LogLevel.Info, context='Context', payload_type='type', payload='hello world')
        dto = LogEntryParser.parse_log_entry(le)
        assert(not isinstance(dto['type'], str))

    def test_payload_should_be_directly_assigned(self):
        le = LogEntry(LogLevel.Info, context='Context', payload_type='type', payload={
            'stuff': 1
        })
        dto = LogEntryParser.parse_log_entry(le)
        assert dto['type'] == le.payload
