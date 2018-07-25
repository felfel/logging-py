from loggingpy import Logger
from loggingpy import BundlingHttpSink
import logging
import sys
from examples import uris  # you must provide these uri strings (just any uri that accepts requests.post(...) requests)

if __name__ == "__main__":
    # Sumologic token url (just a basic string)
    sumoUri = uris.sumoUri

    # Logz.io token url (just a basic string)
    elasticUri = uris.elasticUri

    # these are two sinks of type BatchedHttpSink, which extend the logging.Handler class
    sumoSink = BundlingHttpSink(sumoUri)
    elasticSink = BundlingHttpSink(elasticUri)

    # however, you can use basic logging.Handler derived classes together with the ones here
    stdoutSink = logging.StreamHandler(sys.stdout)

    # configure the logger with a list of handlers to which it pushes the messages
    Logger.with_sinks([sumoSink, elasticSink, stdoutSink])

    # get logger of context
    logger = Logger("Calculator")

    # it is possible to use native loggers with the same name too, which will then log
    native_logger = logging.getLogger('Calculator')
    native_logger.info('Logging via the native logger does work too.')

    # it is possible to make a native logger log its messages in a structured way
    my_logger = logging.getLogger('MoinLogger')
    my_logger.setLevel(logging.DEBUG)
    my_logger.addHandler(sumoSink)
    my_logger.addHandler(elasticSink)
    my_logger.addHandler(stdoutSink)
    my_logger.debug('You can add the handlers to a native logger too to make it log in a structured way.')

    logger2 = Logger('Calculator')
    logger2.info(data='A second logger can be opened and works out of the box.')

    print("Flushing logger...")
    Logger.flush()
    print('...Done.')
