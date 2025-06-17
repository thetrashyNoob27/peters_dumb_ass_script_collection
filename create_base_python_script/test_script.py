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
import json
import re

PROJECT_NAME = "${PROJECT_NAME}"
VERSION_MAJOR = 0
VERSION_MINOR = 0
VERSION_PATCH = 0

ENABLE_LOGGER_4_MODULE = False
logger = logging.getLogger(PROJECT_NAME)


def main(argConfigure) -> None:
    logger.debug("hello,python.")
    time.sleep(1)
    return


class SQLiteHandler(logging.Handler):
    def __init__(self, dbPath: str = None, logKeepSeconds=24 * 60 * 60, logKeepCount=10):
        self.timeFormat = "%Y-%m-%d-%H-%M-%S"
        logging.Handler.__init__(self)
        self._ConnectSqlite(dbPath)
        if self.conn is not None:
            self._removeLog(logKeepSeconds, logKeepCount)
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

    def _ConnectSqlite(self, dbPath: str = None) -> None:
        if dbPath is None:
            dbPath = tempfile.gettempdir()
        db = "{}{}{}.sqlite3".format(
            dbPath, os.path.sep, PROJECT_NAME
        )
        self.db = db
        self.conn = sqlite3.connect(self.db, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.cur = self.conn.cursor()
        self.tableName = "execute-" + datetime.datetime.now().strftime(
            self.timeFormat
        )
        tableCreateCMD = (
                'CREATE TABLE IF NOT EXISTS "%s" (id INTEGER PRIMARY KEY, time TEXT, logSpace TEXT,module TEXT, level TEXT, threadName TEXT, thread TEXT,processID TEXT,fullpath TEXT,file TEXT,function TEXT,line TEXT,stackInfo Text, message TEXT)'
                % (self.tableName)
        )
        try:
            self.cur.execute(tableCreateCMD)
        except sqlite3.OperationalError as e:
            print(f"create table fail:{e}", file=sys.stderr)
            self.conn = None
            return
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

    def _getTables(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        records = cursor.fetchall()
        tableList = []
        for n in records:
            tableList.append(n[0])
        return tableList

    def _removeLog(self, logKeepSeconds, logKeepCount):
        existTables = self._getTables()
        tableTimeList = []
        for name in existTables:
            try:
                tableDate = datetime.datetime.strptime(name, f"execute-{self.timeFormat}")
            except ValueError:
                continue
            tableTimeList.append([name, tableDate])

        toRemoveTables = selectLogToRemove(tableTimeList, logKeepSeconds, logKeepCount)

        self._dropTableList(toRemoveTables)
        return

    def _dropTableList(self, tableList):
        args = []
        for f in tableList:
            args.append((f,))

        cursor = self.conn.cursor()
        for table in tableList:
            cursor.execute(f'DROP TABLE IF EXISTS "{table}";')
        self.conn.commit()
        return

    def _disconnectSqlite(self) -> None:
        if self.conn is None:
            return
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
        if self.conn is None:
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
        if self.conn is None:
            return
        cursur = self.conn.cursor()
        cursur.execute(
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
    _logLevel = getLoggingLevelMap()[argConfigure.logLevel]
    console_handler.setLevel(_logLevel)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logdir = argConfigure.logFilePath
    if logdir == None:
        logdir = tempfile.gettempdir()
    # file
    dateFormat = "%Y-%m-%d-%H-%M-%S"
    logFilePath = "{}{}{}[{}].txt".format(
        logdir,
        os.path.sep,
        PROJECT_NAME,
        datetime.datetime.now().strftime(dateFormat)
    )

    # remove old files
    removeOldLogTxt(dateFormat, logDir=logdir, keepSeconds=argConfigure.logKeepSeconds, keepCount=argConfigure.logKeepCount)

    file_handler = logging.FileHandler(logFilePath)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # sqlite3
    sqlite_handler = SQLiteHandler(logdir, argConfigure.logKeepSeconds, argConfigure.logKeepCount)
    sqlite_handler.setLevel(logging.DEBUG)
    logger.addHandler(sqlite_handler)

    return


def selectLogToRemove(logFiles, keepSeconds, keepCount):
    removeFileList = set()
    # calculate count limit
    fileCounts = len(logFiles)
    if fileCounts > keepCount:

        for record in logFiles[:-keepCount]:
            name = record[0]
            removeFileList.add(name)

    # calculate date limit
    nowTime = datetime.datetime.now()
    for record in logFiles:
        recordTime = record[1]
        if recordTime >= nowTime:
            continue
        difftime = nowTime - recordTime
        diffSec = difftime.seconds
        overdue = diffSec > keepSeconds
        if not overdue:
            continue
        removeFileList.add(record[0])
    return removeFileList


def removeOldLogTxt(dateFormat: str = "%Y-%m-%d-%H-%M-%S", logDir: str = tempfile.gettempdir(), keepSeconds: int = 60 * 60, keepCount: int = 10) -> None:
    logFileNameRe = re.compile(re.escape(PROJECT_NAME) + re.escape('[') + "(.+)" + re.escape(']') + re.escape(".txt"))
    logger.info(f"logFileNameRe:{logFileNameRe}")
    fileList = os.listdir(logDir)
    logFiles = []
    for f in fileList:
        match = logFileNameRe.match(f)
        if not match:
            continue
        dateStr = match.group(1)
        try:
            fileTime = datetime.datetime.strptime(dateStr, dateFormat)
        except ValueError:
            continue
        logFiles.append([f, fileTime])
    logFiles = sorted(logFiles, key=lambda record: record[1].timestamp(), reverse=False)
    for idx, record in enumerate(logFiles):
        logger.info(f"No.{idx} {record[0]} time:{record[1]}")

    removeFileList = selectLogToRemove(logFiles, keepSeconds, keepCount)

    for fname in removeFileList:
        fpath = logDir + os.sep + fname
        try:
            os.remove(fpath)
        except Exception as e:
            print(f"remove log file {fpath} fail:{e}", file=sys.stderr)
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
        "--log-level",
        dest="logLevel",
        type=str.upper,
        choices=list(getLoggingLevelMap()),
        default=list(getLoggingLevelMap())[2],
        help="logging level"
    )
    parser.add_argument(
        "--log-keep-count", type=int, dest="logKeepCount", default=100, help="how many run log record to keep"
    )
    parser.add_argument(
        "--log-keep-second", type=int, dest="logKeepSeconds", default=30 * 24 * 60 * 60, help="how many seconds run log record to keep"
    )
    args = parser.parse_args(argv)

    return args


def logArgs(args: argparse.Namespace) -> None:
    args_dict = vars(args)
    json_str = json.dumps(args_dict, indent=2)
    logger.info(f"process start with args:\n{json_str}")
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


def getLoggingLevelMap() -> dict:
    map = {}
    for level in sorted(logging._levelToName):
        name = logging.getLevelName(level)
        map[name.upper()] = level
    return map


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
