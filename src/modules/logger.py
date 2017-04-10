#!/usr/bin/python
#pylint: disable=relative-import,invalid-name,missing-type-doc,missing-returns-doc,too-many-arguments,global-variable-undefined,global-statement,global-variable-not-assigned
"""Logger
Sets up logging and provides single source and setup for logging.

This class extends out the logger module to store log events as json objects.
Log ingestion systems (i.e. Splunk) can handle and read json natively and
makes it easier to write configs to parse the logs.

This class enforces good behavior when creating logs while being flexible.
Every log must have a message ('msg'), exception needs a reference.

Use:
Logger.info("Something happened")
Logger.info({'msg' : "Something happened"})
Logger.info("Something happened", code="It happened here", status="It smells")
Logger.error({'msg': "Something happened", 'code': "It happened here",
            'status': "It smells"})
Logger.exception("Something happened", exception, status="Not good")
"""

import sys
import os
import json
import datetime as dt
import logging
import logging.handlers
import helpers
import consts

# Levels for logging
LEVELS = {'debug': logging.DEBUG,
          'info': logging.INFO,
          'warning': logging.WARNING,
          'error': logging.ERROR,
          'critical': logging.CRITICAL}

# Based on values from documentation
# https://docs.python.org/2/library/logging.handlers.html#timedrotatingfilehandler
ROTATE_WHEN = "w1"  # Rotates very monday
ROTATE_INTERVAL = 1
ROTATE_BACKUP_COUNT = 5
_log = None


class TimeFormatter(logging.Formatter):
    """Set up time formatting for logging"""

    converter = dt.datetime.fromtimestamp

    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            s = helpers.get_utc()
        return s


def setup_logging(log_file, log_name, is_strict=False,
                  disable_logging=False, is_silent=False, log_path=None):
    """Logging setup must be run before this Logger can be used

    :param log_file: File name
    :param log_name: Log name
    :param is_strict: False - Bool to skip msg in logging message
    :param disable_logging: False - Sets if log files are generated
    :param is_silent: False - Sets if logs are outputted to console
    :param log_path: Set logging path
    :return: None
    """
    global _stream_handler
    global _log
    global _event_log

    global LOG_FILENAME
    global IS_STRICT
    global LOGGING_PATH
    global TRACK_INFO
    global LOG_HANDLER
    global EVENT_LOG_HANDLER

    LOG_FILENAME = "%s.log" % log_file
    IS_STRICT = is_strict

    _log = logging.getLogger(log_name.upper())
    _event_log = logging.getLogger("EVENT_%s" % log_name.upper())

    LOGGING_PATH = log_path if log_path else consts.LOGPATH

    # Logger already defined
    if len(_log.handlers) > 0:
        return True

    debug_on(False)

    # create formatter
    log_format = TimeFormatter(
        fmt=get_format())

    # create event formatter
    event_log_format = TimeFormatter(fmt='%(message)s')

    # allow console output, can be turned off if running silent
    if not is_silent:
        _stream_handler = logging.StreamHandler()
        _log.addHandler(_stream_handler)

    LOG_HANDLER = None

    if not disable_logging:
        # allow logging
        if helpers.create_path(LOGGING_PATH, True):
            LOG_HANDLER = logging.handlers.TimedRotatingFileHandler(
                os.path.join(LOGGING_PATH, LOG_FILENAME), when=ROTATE_WHEN,
                interval=ROTATE_INTERVAL, backupCount=ROTATE_BACKUP_COUNT)

            LOG_HANDLER.setFormatter(log_format)
            _log.addHandler(LOG_HANDLER)

            # Create logger for events
            EVENT_LOG_HANDLER = logging.handlers.TimedRotatingFileHandler(
                os.path.join(LOGGING_PATH, "event_%s" % LOG_FILENAME), when=ROTATE_WHEN,
                interval=ROTATE_INTERVAL, backupCount=ROTATE_BACKUP_COUNT)

            EVENT_LOG_HANDLER.setFormatter(event_log_format)
            _event_log.addHandler(EVENT_LOG_HANDLER)
            _event_log.level = LEVELS['info']
        else:
            _log.error(
                "logging path: %s does not exist and can not be created" %
                LOGGING_PATH)
            return False

    return True


def decide_level(rc):
    """Give level based on return code

    :param rc: return code
    :return: info or error level
    """
    if rc > 0:
        return LEVELS['error']
    return LEVELS['info']


def get_format(track_info=None):
    """Set json logging format

    :param track_info: dict with external information on run
    :return: Json string with logging format
    """

    new_format = '{"datetime": "%(asctime)s",' \
                 '"name": "%(name)s",' \
                 '"level": "%(levelname)s",' \
                 '"log": %(message)s,'

    new_format += '"track": %s}' % (json.dumps(track_info if track_info else helpers.get_track()))

    return new_format


def add_track_info(track_info):
    """Update logging format to include track information

    :param track_info: dict with external information on run
    :return: None
    """
    if LOG_HANDLER:
        log_format = TimeFormatter(
            fmt=get_format(track_info))

        _log.removeHandler(LOG_HANDLER)
        LOG_HANDLER.setFormatter(log_format)
        _log.addHandler(LOG_HANDLER)


def debug_on(is_debug):
    """Sets debug logging flag"""
    if is_debug:
        set_level(logging.DEBUG)
    else:
        set_level(logging.INFO)


def log_event(msg):
    """Log single events - logs just the message body with no wrapper
    :param msg: object to log
    :return:
    """
    _event_log.log(LEVELS['info'], json.dumps(msg))


def debug(msg, **kwargs):
    """Log level debug"""
    log(LEVELS['debug'], msg, **kwargs)


def info(msg, **kwargs):
    """Log level info"""
    log(LEVELS['info'], msg, **kwargs)


def warning(msg, **kwargs):
    """log level warning"""
    log(LEVELS['warning'], msg, **kwargs)

warn = warning


def error(msg, **kwargs):
    """log level error"""
    log(LEVELS['error'], msg, **kwargs)


def errorout(msg, **kwargs):
    """Log level error with app exit"""
    error(msg, **kwargs)
    sys.exit(1)


def exception(msg, e, **kwargs): # pylint: disable=unused-argument
    """log level exception"""
    #msg = _create_log_message(msg, **kwargs)

    # Crashes in default logger libraries when formatting with json.
    # logging\__init__.py: 329
    # _log.exception(msg, e)
    errorout(msg, **kwargs)


def critical(msg, **kwargs):
    """log level critical"""
    log(LEVELS['critical'], msg, **kwargs)
    sys.exit(1)

fatal = critical


def log(level, msg, **kwargs):
    """Main logging function
    :param level: log level
    :param msg: message
    :param kwargs: key values to log
    :return: None
    """
    msg = _create_log_message(msg, **kwargs)

    if not _log:
        print msg
        return

    _log.log(level, msg)


def _create_log_message(msg, **kwargs):
    """Create json log message
    :param msg: message
    :param kwargs: key values to log
    :return: json log message
    """
    if isinstance(msg, dict):
        if "msg" not in msg:
            debug("Include 'msg' key in message.")

            if IS_STRICT:
                sys.exit(1)

        msg_dict = msg.copy()
    else:
        msg_dict = {"msg": msg}

    msg_dict.update(**kwargs)

    return json.dumps(msg_dict, sort_keys=True)


def set_level(value):
    """Set logging level"""
    _log.level = value


@property
def path_check():
    """Check path to see if logging is allowed"""
    return helpers.check_path(LOGGING_PATH, LOG_FILENAME)


class SetLoggingName(object):
    """Class to change the log name temporarily and revert back"""
    def __init__(self, log_name):
        self.log_name = log_name
        self.prev_log = _log.name

    def __enter__(self):
        _log.name = self.log_name
        return _log.name

    def __exit__(self, type, value, tb): # pylint: disable=redefined-builtin
        _log.name = self.prev_log
