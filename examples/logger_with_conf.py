import logging.config
import time
import random
# Say i have saved my configuration under ./myconf.conf
logging.config.fileConfig('myconf.conf')
logger = logging.getLogger('MoinLogger')

logger.info('Test log')
logger.warning('Warning')

i = 0
while True:
    time.sleep(random.randint(10, 50)/1000)
    try:
        1/0
    except:
        i+=1
        print('logging...' + str(i))
        logger.exception("Send some message " + str(i))