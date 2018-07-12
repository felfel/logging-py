from loggingpy.log import Logger
import loggingpy.sink as sink
import time
import random
from examples import uris

if __name__ == "__main__":
    # Sumologic token url
    sumoUri = uris.sumoUri

    # Logz.io token url
    elasticUri = uris.elasticUri

    sumoSink = sink.HttpSink(sumoUri)
    elasticSink = sink.HttpSink(elasticUri)

    logger = Logger([sumoSink, elasticSink], "Calculator")

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

    logger.shutdown()
