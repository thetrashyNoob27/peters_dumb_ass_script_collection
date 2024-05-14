#!/usr/bin/env python3
import os
import argparse
import logging
import tempfile
import datetime
import sqlite3
import shlex
import subprocess
import mimetypes
import sys
import shutil


PROJECT_NAME = "pull_media"
VERSION_MAJOR = 0
VERSION_MINOR = 0
VERSION_PATCH = 0

logger = logging.getLogger(PROJECT_NAME)


def fileType(path):
    ftype = mimetypes.guess_type(path)[0]
    if ftype is None:
        return None
    return ftype.split('/')[0]


def extentsionIsMediaType(fname):
    if len(fname) == 0:
        return False
    fsep = fname.split('.')
    if len(fsep) < 2:
        return False
    ext = fsep[-1].lower()
    mediaExtentionList = ['jpg', 'gif', 'png', 'bmp', 'svg', 'jpeg', 'ico', 'xcf', 'vtf', 'psd', 'pbm', 'ppm', 'xpm',
                          'xbm', 'gz', 'heic', 'b16', 'pat', 'sgi', 'pgm', 'tiff', 'ras', 'exr', 'fbs', 'wbmp', 'ktx',
                          'cdr', 'fits', 'rgb', 'pcx', 'xwd', 'wmf', 'cgm', 'jng', 'jp2', 'fpx', 'pnm', 'tap', 'orf',
                          'nef', 'cr2', 'cpt', 'tif', 'heif', 'mp4', 'mpg', 'bk2', 'bik', 'wmv', 'avi', 'mkv', 'dl',
                          'mov', 'webm', 'm2v', 'mng', 'flv', 'gl', 'ogv', 'm4v', 'amr', 'aac', 'wav', 'awb', 'mp3',
                          'ogg', 'flac', 'csd', 'wma', 'dts', 'smp', 'aif', 'sco', 'mxmf', 'mid', 'au', 'aiff', 'aifc',
                          'opus', 'adts', 'ac3', 'm4a', '3gp', 'm3u', 'pls', 'mp2', 'ass']
    return ext in mediaExtentionList


def findFiles(deviceID, skipPath=[], disable_nomedia=False):
    findres = subprocess.run(['adb', '-s', deviceID, 'shell',
                             'find /sdcard/ -type f'], capture_output=True, text=True)
    fileList = findres.stdout.split('\n')

    nomediares = subprocess.run(['adb', '-s', deviceID, 'shell',
                                 'find /sdcard/ -type f -name \'.nomedia\''], capture_output=True, text=True)
    nomediaFileList = nomediares.stdout.split('\n')
    nomediaPath = []
    for nm in nomediaFileList:
        if len(nm) == 0:
            continue
        nomediaPath.append(os.path.dirname(nm))
    del nomediaFileList

    fList = []
    for f in fileList:
        if len(f) == 0:
            continue
        # nomedia path skip
        if not disable_nomedia:
            base = os.path.dirname(f)
            if base in nomediaPath:
                continue
        # arg --skip path
        _skip = False
        for skip in skipPath:
            # logger.debug(f"file:{f} check skip: {skip} res:{f.find(skip)}")
            if f.find(skip) == 0:
                _skip = True
                break
        if _skip:
            continue
        fList.append(f)
    fileList = fList
    return fileList


def adbcheckfileSize(deviceID, path):
    try:
        res = subprocess.run(['adb', '-s', deviceID, 'shell', 'ls -l %s' %
                             (shlex.quote(path))], capture_output=True, text=True, encoding="utf-8")
    except UnicodeDecodeError as e:
        print("cant stats file: ->%s<-" % (path))
        return -1
    if res.returncode != 0:
        return -1
    return int(res.stdout.split(' ')[4])


def main(argConfigure) -> None:
    logger.debug(f"programe run args:{argConfigure}")
    checkDevicesReturn = subprocess.run(
        ['adb', 'devices'], capture_output=True, text=True)
    if checkDevicesReturn.returncode != 0:
        eprint("adb command error")
        sys.exit(1)

    deviceIDList = []
    deviceStr = checkDevicesReturn.stdout.split("\n")

    for l in deviceStr[1:]:
        if len(l) == 0:
            continue
        deviceIDList.append(l.split('\t')[0])

    for deviceID in deviceIDList:
        flist = findFiles(deviceID, argConfigure.skip,
                          argConfigure.ignoreNomedia)
        print("pulling from device:%s" % (deviceID))
        existDirList = []
        for f in flist:
            f = f.strip()
            if not extentsionIsMediaType(f):
                continue
            if f.find("/sdcard/") != 0:
                continue
            sdcardPath = f[len("/sdcard/"):]
            pulldirName = os.path.dirname(sdcardPath)
            fileName = os.path.basename(f)
            if pulldirName not in existDirList:
                if not os.path.exists(pulldirName):
                    os.makedirs(pulldirName)
                existDirList.append(pulldirName)

            if os.path.exists(sdcardPath):
                phoneFileSize = adbcheckfileSize(deviceID, f)
                thisFileSize = os.path.getsize(sdcardPath)
                # print("pth:%s phone size:%d this size%d" %(f,phoneFileSize,thisFileSize))
                if phoneFileSize == thisFileSize or phoneFileSize == 0:
                    continue
                else:
                    os.remove(sdcardPath)

            pullres = subprocess.run(
                ['adb', '-s', deviceID, 'pull', f, sdcardPath])
            if pullres.returncode != 0:
                continue
            if fileType(sdcardPath) not in ['video', 'image', 'audio']:
                os.remove(sdcardPath)
                pass


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


def log_init(LogFilePath: str) -> None:
    logger = logging.getLogger(PROJECT_NAME)
    logger.setLevel(logging.DEBUG)

    # format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # STDOUT
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logdir = LogFilePath
    if LogFilePath == None:
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

    parser.add_argument(
        '-s', '--skip', default=["/sdcard/Android", "/sdcard/Movies", "/sdcard/Music"], nargs='+', help='skip path')

    parser.add_argument('--ignore-nomedia', dest='ignoreNomedia',
                        action='store_true', help='enable, default=False')
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
    log_init(argConfigure.logFilePath)
    logger.info(f"project: {PROJECT_NAME}")
    logger.info(f"version: {VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}")
    logger.info(f"process args:{argConfigure.__str__()}")
    logger.info(f"script path:{scriptDir()}")
    logArgs(argConfigure)
    main(argConfigure)
# create by base python script creator 0.2.0
# create on  [+0800]2024-05-14 16:52:54
