#!/usr/bin/bash
read -p "project name:" PROJECT_NAME;
echo "${PROJECT_NAME}";

if [[ -z "$PROJECT_NAME" ]]; then
    echo "project name empty.";
    exit;
fi
if [[ -f "$PROJECT_NAME.py" ]]; then
    echo "file exist.";
    exit;
fi

cat<<EOF >"${PROJECT_NAME}.py"
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
import psutil
import json
import signal
import multiprocessing

PROJECT_NAME = "${PROJECT_NAME}"
VERSION_MAJOR = 0
VERSION_MINOR = 0
VERSION_PATCH = 0

ENABLE_LOGGER_4_MODULE = False
logger = logging.getLogger(PROJECT_NAME)


def main(argConfigure) -> None:
    logger.info("hello,python.")
    time.sleep(1)
    logger.info(f"start log proformance test")
    for i in range(0, 1000):
        logger.debug(f"{i}")
    logger.info(f"finish log proformance test")
    return


class SQLiteHandler(logging.Handler):
    def __init__(self, db: str = None):
        logging.Handler.__init__(self)
        self.dbName = db
        self._ProcessSeprate()
        # parent thread run here

    def _ProcessSeprate(self) -> None:
        self.HostPID = os.getppid()
        self.writePID = None
        self.messageQueue = multiprocessing.Queue(1000)
        self.writeProcess = multiprocessing.Process(
            target=self.WriteProcessLogic, args=()
        )
        self.writeProcess.daemon = True
        self.writeProcess.start()
        return

    def __del__(self) -> None:
        if not self._isWriteProcess():
            pass
        return

    def _isWriteProcess(self) -> None:
        thisPID = os.getpid()
        isChild = self.writePID is not None
        return isChild

    def _ConnectSqLite(self, db: str = None) -> None:
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
        if self._isWriteProcess():
            print(f"Sqlite sink writer thread not supposed to emit()", file=sys.stderr)
            return
        if self.messageQueue.full():
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

        self.messageQueue.put(json.dumps(msg))
        return

    def close(self) -> None:
        if self._isWriteProcess():
            self.conn.close()
            self.cur = None
            self.conn = None
        else:
            logging.Handler.close(self)

    def WriteProcessSignalHandler(self, sig, frame) -> None:
        if sig == signal.SIGTERM:
            self.messageQueue.put(None)
        return

    def SinkWriteJob(self) -> None:
        while True:
            msg = self.messageQueue.get()
            if msg is None:
                break
            msg = json.loads(msg)
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
        self.conn.commit()
        self.cur.execute("PRAGMA wal_checkpoint;")
        return

    def WriteProcessLogic(self) -> None:
        signal.signal(signal.SIGTERM, self.WriteProcessSignalHandler)
        self._ConnectSqLite(self.dbName)
        self.SinkWriteThread = threading.Thread(target=self.SinkWriteJob, daemon=True)
        self.SinkWriteThread.start()
        self.SinkWriteThread.join()
        self.close()
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
#create by base python script creator 0.5.0
EOF

echo "# create on $(date "+ [%z]%F %H:%M:%S")">>"${PROJECT_NAME}.py";
chmod a+x "${PROJECT_NAME}.py";
