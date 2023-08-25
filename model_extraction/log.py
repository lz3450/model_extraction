import logging


def config_logger(logger: logging.Logger):
    logger.setLevel(logging.INFO)
    logger.propagate = False
    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # create formatter
    # formatter = logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    formatter = logging.Formatter('[%(name)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # add formatter to ch
    ch.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(ch)
