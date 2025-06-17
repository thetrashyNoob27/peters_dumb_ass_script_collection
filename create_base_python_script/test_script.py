#!/usr/bin/env python3
import os
import sys
import argparse
import logging
import tempfile
import datetime
import sqlite3
import time
import threading
import queue

PROJECT_NAME = "${PROJECT_NAME}"
VERSION_MAJOR = 0
VERSION_MINOR = 0
VERSION_PATCH = 0

ENABLE_LOGGER_4_MODULE = False
logger = logging.getLogger(PROJECT_NAME)


def loggingProformanceTest(writeCount: int = 1000):
    start = time.monotonic()
    logger.info(f"start log proformance test")
    for i in range(0, writeCount):
        logger.debug(f"{i}")
    logger.info(f"finish log proformance test")
    end = time.monotonic()

    timeuseMS = (end - start) * 1000
    logPerSec = writeCount / (end - start)
    logger.info(f"{writeCount} log write timeuse :{timeuseMS:3f}ms ({logPerSec:2f}L/Sec)")
    return


def main(argConfigure) -> None:
    logger.info("hello,python.")
    time.sleep(1)
    loggingProformanceTest(10000)
    return


class SQLiteHandler(logging.Handler):
    def __init__(self, db: str = None):
        logging.Handler.__init__(self)
        self.dbName = db
        self._ConnectSqlite()
        self._startWriterThread()

    def __del__(self) -> None:
        self.close()
        return

    def _startWriterThread(self) -> None:
        self.pendingWriteLogRecordQueue = queue.Queue()
        self.pendingWriteLogRecordLock = threading.Lock()
        self.pendingWriteLogRecordCondition = threading.Condition(self.pendingWriteLogRecordLock)
        self.writerThreadQuit = False

        self.SinkWriteThread = threading.Thread(target=self.SinkWriteJob, daemon=True)
        self.SinkWriteThread.start()
        return

    def _stopWriterThread(self) -> None:
        self.writerThreadQuit = True
        with self.pendingWriteLogRecordCondition:
            if not self.SinkWriteThread.is_alive():
                return
            self.pendingWriteLogRecordCondition.notify_all()
        self.SinkWriteThread.join()
        return

    def _ConnectSqlite(self, db: str = None) -> None:
        if db == None:
            db = "{}{}{}.sqlite3".format(
                tempfile.gettempdir(), os.path.sep, PROJECT_NAME
            )
        self.db = db
        self.conn = sqlite3.connect(self.db, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.cur = self.conn.cursor()
        self.tableName = "execute-" + datetime.datetime.now().strftime(
            "%Y-%m-%d-%H-%M-%S"
        )
        tableCreateCMD = (
                'CREATE TABLE IF NOT EXISTS "%s" (id INTEGER PRIMARY KEY, time TEXT, logSpace TEXT,module TEXT, level TEXT, threadName TEXT, thread TEXT,processID TEXT,fullpath TEXT,file TEXT,function TEXT,line TEXT,stackInfo Text, message TEXT)'
                % (self.tableName)
        )
        self.cur.execute(tableCreateCMD)
        self.conn.commit()


        self.instertCMD = self._INSERT_builder(
            [
                "time",
                "logSpace",
                "module",
                "level",
                "threadName",
                "thread",
                "processID",
                "fullpath",
                "file",
                "function",
                "line",
                "stackInfo",
                "message",
            ]
        )
        return

    def _disconnectSqlite(self) -> None:
        self.conn.commit()
        self.conn.close()
        return

    def _INSERT_builder(self, infos: list) -> str:
        cmd = 'INSERT INTO "%s" ' % (self.tableName)
        columnStr = "("
        bindValueStr = "("
        for k in infos:
            columnStr += '"'
            columnStr += k
            columnStr += '",'
            bindValueStr += "?,"
        columnStr = columnStr[:-1]
        bindValueStr = bindValueStr[:-1]
        columnStr += ")"
        bindValueStr += ")"
        cmd = cmd + columnStr + " VALUES " + bindValueStr
        return cmd

    def emit(self, record: logging.LogRecord) -> None:
        if self.pendingWriteLogRecordQueue.full():
            print(f"message queue fill. cant log to sqlite writer", file=sys.stderr)
            return

        msg = dict()
        msg["asctime"] = f"{record.asctime}.{int(record.msecs):03d}"
        msg["name"] = record.name
        msg["module"] = record.module
        msg["levelname"] = record.levelname
        msg["threadName"] = record.threadName
        msg["thread"] = record.thread
        msg["process"] = record.process
        msg["pathname"] = record.pathname
        msg["filename"] = record.filename
        msg["funcName"] = record.funcName
        msg["lineno"] = record.lineno
        msg["stack_info"] = record.stack_info
        msg["message"] = record.message

        with self.pendingWriteLogRecordCondition:
            self.pendingWriteLogRecordQueue.put(msg)
            self.pendingWriteLogRecordCondition.notify_all()
        return

    def close(self) -> None:
        self._stopWriterThread()
        self._disconnectSqlite()
        return

    def writeLogRecord(self, msg) -> None:
        self.cur.execute(
            self.instertCMD,
            (
                msg["asctime"],
                msg["name"],
                msg["module"],
                msg["levelname"],
                msg["threadName"],
                msg["thread"],
                msg["process"],
                msg["pathname"],
                msg["filename"],
                msg["funcName"],
                msg["lineno"],
                msg["stack_info"],
                msg["message"],
            ),
        )
        return

    def SinkWriteJob(self) -> None:
        while True:
            with self.pendingWriteLogRecordCondition:
                while self.pendingWriteLogRecordQueue.empty() and not self.writerThreadQuit:
                    self.pendingWriteLogRecordCondition.wait()

                if self.writerThreadQuit and self.pendingWriteLogRecordQueue.empty():
                    break
                msg = self.pendingWriteLogRecordQueue.get()
            self.writeLogRecord(msg)
        self.conn.commit()
        return


def log_init(argConfigure) -> None:
    logger = logging.getLogger(PROJECT_NAME)
    logger.setLevel(logging.DEBUG)

    # format
    formatter = logging.Formatter(
        "[%(asctime)s.%(msecs)03d][%(name)s][%(levelname)s][%(filename)s:%(lineno)d (%(funcName)s)]-> %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # STDOUT
    console_handler = logging.StreamHandler()
    if argConfigure.verbose:
        console_handler.setLevel(logging.DEBUG)
    else:
        console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logdir = argConfigure.logFilePath
    if logdir == None:
        logdir = tempfile.gettempdir()
    # file
    logFilePath = "{}{}{}[{}].txt".format(
        logdir,
        os.path.sep,
        PROJECT_NAME,
        datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
    )
    file_handler = logging.FileHandler(logFilePath)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # sqlite3
    dbFileName = "{}{}{}.sqlite3".format(logdir, os.path.sep, PROJECT_NAME)
    sqlite_handler = SQLiteHandler(dbFileName)
    sqlite_handler.setLevel(logging.DEBUG)
    logger.addHandler(sqlite_handler)

    return


def argProcess(argv: sys.argv[1:]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=PROJECT_NAME)

    parser.add_argument(
        "--log-file-path", default=None, dest="logFilePath", help="log file path"
    )

    parser.add_argument("-s", "--string", nargs="+", help="strings input")
    parser.add_argument(
        "-n",
        "--number",
        type=float,
        default=3.141592654,
        help="float number, with default π",
    )
    parser.add_argument(
        "-e", "--enable", action="store_true", help="enable, default=False"
    )
    parser.add_argument(
        "-v", action="store_true", dest="verbose", help="enable script nagging"
    )
    args = parser.parse_args(argv)

    return args


def logArgs(args: argparse.Namespace) -> None:
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


def GlobalExceptionHandler(exc_type, exc_value, exc_tb) -> None:
    import traceback

    traceback_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logger.error(f"{traceback_str}")
    return


if __name__ == "__main__" or ENABLE_LOGGER_4_MODULE:
    argConfigure = argProcess(sys.argv[1:])
    log_init(argConfigure)
    sys.excepthook = GlobalExceptionHandler
    logger.info(f"project: {PROJECT_NAME}")
    logger.info(f"version: {VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}")
    logger.info(f"process args:{argConfigure.__str__()}")
    logger.info(f"script path:{scriptDir()}")
    logArgs(argConfigure)
else:
    # as module
    pass

if __name__ == "__main__":
    main(argConfigure)
