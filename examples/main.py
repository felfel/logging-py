from loggingpy import Logger
from loggingpy import HttpSink
import time
import random
import logging
import sys
from examples import uris  # you must provide these uri strings (just any uri that accepts requests.post(...) requests)

if __name__ == "__main__":
    # Sumologic token url (just a basic string)
    sumoUri = uris.sumoUri

    # Logz.io token url (just a basic string)
    elasticUri = uris.elasticUri

    # these are two sinks of type HttpSink, which extend the logging.Handler class
    sumoSink = HttpSink(sumoUri)
    elasticSink = HttpSink(elasticUri)

    # however, you can use basic logging.Handler derived classes together with the ones here
    stdoutSink = logging.StreamHandler(sys.stdout)

    # configure the logger with a list of handlers to which it pushes the messages
    Logger.with_sinks([sumoSink, elasticSink, stdoutSink])

    # get logger of context
    logger = Logger("Calculator")

    # this is just some basic code that generates different types of exceptions and then pushes different messages
    try:
        for i in range(0, 100000):
            try:
                div = random.randint(0, 20)
                x = 123 / div

                if div == 1:
                    raise Exception("Because I can")

                logger.warning(payload_type="MathOperation", data={
                    "OperationType": "Division",
                    "OperationDetails": {
                        "Div": div,
                        "Result": x
                        }
                    }
                )

            except Exception as e:
                logger.fatal(e, "CalculationError", {"Message": "What the fck just happened???"})

            if i % 100 == 0:
                time.sleep(random.randint(10, 5000)/1000)

            if i % 500 == 0:
                print("Got " + str(i))
    except BaseException as e:  # this catch is required in order to shutdown the logger properly
        pass

    print("Flushing logger...")
    logger.flush()
    print('...Done.')
