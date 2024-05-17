#!/usr/bin/env python3
import os
import argparse
import logging
import tempfile
import datetime
import sqlite3

PROJECT_NAME = "${PROJECT_NAME}"
VERSION_MAJOR = 0
VERSION_MINOR = 0
VERSION_PATCH = 0

logger = logging.getLogger(PROJECT_NAME)


def main(argConfigure) -> None:
    print("hello,python.")
    return


class SQLiteHandler(logging.Handler):
    def __init__(self, db: str = None):
        logging.Handler.__init__(self)
        if db == None:
            db = "{}{}{}.sqlite3".format(
                tempfile.gettempdir(), os.path.sep, PROJECT_NAME)
        self.db = db
        self.conn = sqlite3.connect(self.db)
        self.conn.execute('PRAGMA journal_mode = WAL')
        self.cur = self.conn.cursor()
        self.tableName = "execute-"+datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        tableCreateCMD = "CREATE TABLE IF NOT EXISTS \"%s\" (id INTEGER PRIMARY KEY, time TEXT, logSpace TEXT,module TEXT, level TEXT, threadName TEXT, thread TEXT,processID TEXT,fullpath TEXT,file TEXT,function TEXT,line TEXT,stackInfo Text, message TEXT)" % (
            self.tableName)
        self.cur.execute(tableCreateCMD)
        self.conn.commit()

        self.instertCMD = self._INSERT_builder(['time', 'logSpace', 'module', 'level', 'threadName',
                                                'thread', 'processID', 'fullpath', 'file', 'function', 'line', 'stackInfo', 'message'])

    def _INSERT_builder(self, infos: list) -> str:
        cmd = "INSERT INTO \"%s\" " % (self.tableName)
        columnStr = "("
        bindValueStr = "("
        for k in infos:
            columnStr += "\""
            columnStr += k
            columnStr += "\","
            bindValueStr += "?,"
        columnStr = columnStr[:-1]
        bindValueStr = bindValueStr[:-1]
        columnStr += ")"
        bindValueStr += ")"
        cmd = cmd + columnStr+" VALUES "+bindValueStr
        return cmd

    def emit(self, record: logging.LogRecord) -> None:
        self.cur.execute(self.instertCMD, (record.asctime, record.name, record.module, record.levelname, record.threadName,
                         record.thread, record.process, record.pathname, record.filename, record.funcName, record.lineno, record.stack_info, record.message))
        self.conn.commit()
        return

    def close(self) -> None:
        self.conn.close()
        logging.Handler.close(self)


def log_init(argConfigure) -> None:
    logger = logging.getLogger(PROJECT_NAME)
    logger.setLevel(logging.DEBUG)

    # format
    formatter = logging.Formatter(
        '[%(asctime)s.%(msecs)03d][%(name)s][%(levelname)s][%(filename)s:%(lineno)d (%(funcName)s)]-> %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # STDOUT
    console_handler = logging.StreamHandler()
    if argConfigure.verbose:
        console_handler.setLevel(logger.DEBUG)
    else:
        console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logdir = argConfigure.logFilePath
    if logdir == None:
        logdir = tempfile.gettempdir()
    # file
    logFilePath = "{}{}{}[{}].txt".format(
        logdir, os.path.sep, PROJECT_NAME, datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"))
    file_handler = logging.FileHandler(logFilePath)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # sqlite3
    dbFileName = "{}{}{}.sqlite3".format(logdir,
                                         os.path.sep, PROJECT_NAME)
    sqlite_handler = SQLiteHandler(dbFileName)
    sqlite_handler.setLevel(logging.DEBUG)
    logger.addHandler(sqlite_handler)

    return


def argProcess() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=PROJECT_NAME)

    parser.add_argument('--log-file-path', default=None,
                        dest='logFilePath', help='log file path')

    parser.add_argument('-s', '--string', nargs='+', help='strings input')
    parser.add_argument('-n', '--number', type=float,
                        default=3.141592654, help='float number, with default π')
    parser.add_argument(
        '-e', '--enable', action='store_true', help='enable, default=False')
    parser.add_argument(
        '-v', action='store_true', dest='verbose', help='enable script nagging')
    args = parser.parse_args()

    return args


def logArgs(args: argparse.Namespace):
    args_dict = vars(args)
    logstr = ""
    for key, value in args_dict.items():
        logstr += "%s:%s" % (key, value)
        logstr += "\n"
    logger.info(logstr)
    return


def scriptDir() -> str:
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    return script_dir


if __name__ == "__main__":
    argConfigure = argProcess()
    log_init(argConfigure)
    logger.info(f"project: {PROJECT_NAME}")
    logger.info(f"version: {VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}")
    logger.info(f"process args:{argConfigure.__str__()}")
    logger.info(f"script path:{scriptDir()}")
    logArgs(argConfigure)
    main(argConfigure)
