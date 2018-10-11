from enum import Enum
import datetime
import pytz
import traceback
import logging
import logging.handlers
import queue
import json
import hashlib
import random
import re
import uuid
from loggingpy.exceptions import ExceptionInfo
from typing import Union


class LogLevel(Enum):
    """
    We need our own log level enum in order to produce the proper names in the dto level attribute.
    """
    Debug = 10
    Info = 20
    Warning = 30
    Error = 40
    Fatal = 50


class LogEntry:
    """
    A log entry consists of a log level, a timestamp, a context and a payload ( which are all required)
    and from data and exception information (both optional).
    """

    def __init__(
        self,
        log_level: Enum,
        context: str,
        payload_type: str,
        timestamp: datetime=None,
        message='',
        payload=None,
        exception: Exception=None
    ):
        
        # timestamp default must be set here because in the signature it is set to init time
        if timestamp is None:
            timestamp = pytz.UTC.localize(datetime.datetime.utcnow())
        else:
            if not timestamp.tzinfo:
                raise ValueError("Timestamp provided should not be naive")

        self.timestamp = timestamp
        self.context = context
        self.payload_type = payload_type
        self.log_level = log_level
        self.message = message
        self.payload = payload
        self.exception = exception


class LogEntryParser:
    """
    The Log entry parser helps to turn log entries into serializable data for the logger.
    """

    @staticmethod
    def exception_to_string(exception: Exception):
        """
        Turn an exception into a string.
        :param exception:
        :return:
        """
        stack = traceback.extract_tb(exception.__traceback__)
        pretty = traceback.format_list(stack)
        return ''.join(pretty) + '\n  {} {}'.format(exception.__class__, exception)

    @staticmethod
    def hash_exception(exception: Exception):
        """
        Create a hierarchical hash of the exception.
        :param exception:
        :return:
        """
        stack_trace = LogEntryParser.exception_to_string(exception)
        stack_trace_lines = stack_trace.split('\n')
        stack_trace_lines = stack_trace_lines[:-2]
        stack_trace_lines[-1] = stack_trace_lines[-1].split('(')[0]

        # TBD: this routine would just create a single(32 character) hash of all exceptions:
        # return hashlib.md5(''.join(stack_trace_lines).encode('utf-8'))

        # if the list contains more than 10 hashes, trim it down by concatenating some
        while len(stack_trace_lines) > 10:
            stack_trace_lines[-2] = stack_trace_lines[-2] + stack_trace_lines[-1]
            stack_trace_lines.pop(-1)

        stack_hash = [hashlib.md5(s.encode('utf-8')).hexdigest() for s in stack_trace_lines]

        # an MD5 hash has 32 characters - trim it down to 8 chars, risk of collisions is basically zero
        # and it's wouldn't even be that much of a problem with proper logging (different context info, too)
        hashes = [l[:8] for l in stack_hash]
        return '.'.join(hashes)

    @staticmethod
    def parse_log_entry(log_entry: LogEntry):
        """
        Parse the log entry into a data transfer object (basically a dictionary).
        :param log_entry:
        :return:
        """
        exception = log_entry.exception
        if exception is not None:
            exception_info = ExceptionInfo(exception_type=exception.__class__.__name__,
                                           error_message=str(exception),
                                           stack_trace=LogEntryParser.exception_to_string(exception),
                                           exception_hash=LogEntryParser.hash_exception(exception))
        else:
            exception_info = None

        # transparently wrap string values into an object to ensure a logged payload is always a JSON object rather
        # than a scalar. We do not care about other primitives etc. If somebody is willing to log an int, it'll just
        # get serialized
        payload = log_entry.payload

        if type(payload) is str:                                                # turn string to json
            payload = {"Message": payload}

        dto = {                                                                 # build a dto
            "timestamp": log_entry.timestamp,
            "level": log_entry.log_level.name,
            "context": "" if log_entry.context is None else log_entry.context,
        }

        if log_entry.payload_type is not None and log_entry.payload_type != '':  # add payload type if any
            dto["payload_type"] = log_entry.payload_type

            if payload is not None:
                property_name = dto['payload_type'].replace('.', '_')
                property_name = LogEntryParser.underscore(property_name)
                dto[property_name] = payload                                # add payload if any

        if log_entry.message is not "" and log_entry.message is not None:   # add message if any
            dto["message"] = log_entry.message

        if exception_info is not None:                                      # add exception if any
            dto["exception_info"] = {
                "exception_type": exception_info.exception_type,
                "error_message": exception_info.error_message,
                "stack_trace": exception_info.stack_trace,
                "exception_hash": exception_info.exception_hash
            }

        return dto

    @staticmethod
    def underscore(word):
        # from https://github.com/jpvanhal/inflection/blob/2ea54f615924c5cfc967d50cc179eacf0b269c08/inflection.py#L394
        # if you require more of this library, consider getting it as a dependency
        """
        Make an underscored, lowercase form from the expression in the string.
        Example::
            >>> underscore("DeviceType")
            "device_type"
        As a rule of thumb you can think of :func:`underscore` as the inverse of
        :func:`camelize`, though there are cases where that does not hold::
            >>> camelize(underscore("IOError"))
            "IoError"
        """
        word = re.sub(r"([A-Z]+)([A-Z][a-z])", r'\1_\2', word)
        word = re.sub(r"([a-z\d])([A-Z])", r'\1_\2', word)
        word = word.replace("-", "_")
        return word.lower()


class Logger:
    """
    The structured logger is just a wrapper around the builtin standard python logger. It simplifies the interface of
    logging to make proper structured logger calls.
    """
    sinks = []

    @staticmethod
    def with_sinks(sinks: list):
        """
        Append the given sinks to all structured loggers.
        :param sinks:
        :return:
        """
        for sink in sinks:
            Logger.with_sink(sink)

    @staticmethod
    def with_sink(sink):
        """
        Append the given sink to all structured loggers.
        :param sink:
        :return:
        """
        Logger.sinks.append(sink)
        sink.setFormatter(JsonFormatter())  # all appended sinks get the json formatter in order to log only structured messages

    def __init__(self, context: str, prefix_payload_type: bool = True):
        self.context = context
        self.logger = logging.getLogger(context)
        self.handlers = []
        self.prefix_payload_type = prefix_payload_type

        if len(self.logger.handlers) == 0:
            for sink in Logger.sinks:
                # each sink we add to the logger gets a queue handler prepended in order to allow the message to enqueue
                # and thereby make the logger non-blocking to the code
                log_queue = queue.Queue(-1)
                queue_handler = logging.handlers.QueueHandler(log_queue)
                queue_listener = logging.handlers.QueueListener(log_queue, sink)
                queue_listener.start()

                # we collect the handlers in order to be able to flush them at the end and ensure graceful shutdown
                self.handlers.append(sink)
                self.logger.addHandler(queue_handler)
        else:
            self.handlers.extend(Logger.sinks)

    def set_level(self, level):
        """
        Set the general log level.
        :param level:
        :return:
        """
        self.logger.setLevel(level)

    def _log(self, log_entry: LogEntry):
        if log_entry.context is None or log_entry.context is "":
            log_entry.context = self.context

        self.logger.log(log_entry.log_level.value, log_entry.message, extra={'log_entry': log_entry})  # exc_info=True, stack_info=True, add this to drop out some dto info

    def _write_entry(self, log_level: Enum, payload_type: str, message: str= '', payload=None, exception: Exception = None):

        second_log_entry = None
        if payload is not None and payload_type is '':
            payload_type = 'MissingPayloadType' + str(random.randint(0, 1000000))
            second_log_entry = LogEntry(context="",
                                 log_level=log_level,
                                 payload_type='',
                                 message="The previous message lacks a payload type, but appends payload."
                                         " Autogenerated payload type "
                                         + payload_type +
                                         ". Don't be lazy, add a payload type.")

        if self.context and self.prefix_payload_type:
            payload_type = self.context + '.' + payload_type

        log_entry = LogEntry(context="",
                             log_level=log_level,
                             payload_type=payload_type,
                             message=message,
                             payload=payload,
                             exception=exception)
        self._log(log_entry)

        if second_log_entry is not None:
            self._log(second_log_entry)

    # convenience methods

    def debug(self, message: str='', exception: Exception=None, payload_type: str='', payload: Union[str, dict]=None):
        self._write_entry(LogLevel.Debug, payload_type=payload_type, message=message, payload=payload, exception=exception)

    def info(self, message: str='', exception: Exception=None, payload_type: str='', payload: Union[str, dict]=None):
        self._write_entry(LogLevel.Info, payload_type=payload_type, message=message, payload=payload, exception=exception)

    def warning(self, message: str='', exception: Exception=None, payload_type: str='', payload: Union[str, dict]=None):
        self._write_entry(LogLevel.Warning, payload_type=payload_type, message=message, payload=payload, exception=exception)

    def error(self, message: str='', exception: Exception=None, payload_type: str='', payload: Union[str, dict]=None):
        self._write_entry(LogLevel.Error, payload_type=payload_type, message=message, payload=payload, exception=exception)

    def fatal(self, message: str='', exception: Exception=None, payload_type: str='', payload: Union[str, dict]=None):
        self._write_entry(LogLevel.Fatal, payload_type=payload_type, message=message, payload=payload, exception=exception)

    @staticmethod
    def flush():
        """
        Flush all sinks.
        :return:
        """
        [h.flush() for h in Logger.sinks]


class JsonFormatter(logging.Formatter):
    """
    The Json formatter turns all types of classes into dictionaries, and then formats it into a json.
    """

    def __init__(self, fmt=None, datefmt=None, style='%'):
        logging.Formatter.__init__(self, fmt, datefmt, style)

    def to_dict(self, obj, classkey=None):
        """
        This method allows us to turn arbitrary objects into dictionaries. This should be sufficient for most purposes.
        :param classkey:
        :return:
        """
        if isinstance(obj, dict):
            data = {}
            for (k, v) in obj.items():
                data[k] = self.to_dict(v, classkey)
            return data

        elif isinstance(obj, uuid.UUID):
            """
            Special case for UUID, if not __dict__ repr of uuid will be returned
            """
            return str(obj)

        elif hasattr(obj, "_ast"):
            return self.to_dict(obj._ast())

        elif hasattr(obj, "__iter__") and not isinstance(obj, str):
            return [self.to_dict(v, classkey) for v in obj]

        elif hasattr(obj, "__dict__"):
            data = dict([(key, self.to_dict(value, classkey))
                         for key, value in obj.__dict__.items()
                         if not callable(value) and not key.startswith('_')])
            if classkey is not None and hasattr(obj, "__class__"):
                data[classkey] = obj.__class__.__name__
            return data

        else:
            return obj

    def format(self, record):
        """Formats a log record and serializes to json"""

        record.msg = logging.Formatter.format(self, record)  # format the message using the base formatter

        if hasattr(record, 'log_entry'):
            log_entry = record.log_entry
        else:
            log_entry = LogEntry(log_level=LogLevel(record.levelno),
                                 context=record.name,
                                 payload_type='ExternalLoggerMessage',
                                 message=record.msg)

        dto = LogEntryParser.parse_log_entry(log_entry=log_entry)   # turn the log entry into a dto for serialization

        if hasattr(record, 'app_name'):
            dto['app_name'] = record.app_name

        try:
            json_dto = json.dumps(self.to_dict(dto), default=str)   # turn dto to json
        except Exception as e:  # if it fails to serialize the dto
            json_dto = json.dumps(self.to_dict({
                "timestamp": datetime.datetime.utcnow(),
                "message": "Could not unwrap log entry.",
                "level": LogLevel.Fatal,
                "context": "Logging.Error",
                "payload_type": "UnwrapError",
                "logging_error": LogEntryParser.exception_to_string(e)
            }))

        return json_dto


