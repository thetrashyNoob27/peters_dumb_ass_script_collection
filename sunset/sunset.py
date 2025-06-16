#!/usr/bin/env python3
import os
import argparse
import logging
import tempfile
import datetime
import sqlite3
import nature_const
import numpy as np
import math
import copy

PROJECT_NAME = "sunset"
VERSION_MAJOR = 0
VERSION_MINOR = 0
VERSION_PATCH = 0

logger = logging.getLogger(PROJECT_NAME)


class location:
    """
    3-d location stored by 3,1 numpy matrix
    order (x,y,z)
    """

    def __init__(self, x=0, y=0, z=0):
        self.pos = np.matrix(np.zeros(shape=(3, 1)))
        self.x(x)
        self.y(y)
        self.z(z)
        return

    def __add__(self, other):
        sum = location()
        sum.pos = self.pos + other.pos

        return sum

    def __sub__(self, other):
        sub = location()
        sub.pos = self.pos - other.pos
        return sub

    def x(self, v):
        self.pos[0] = v
        return

    def y(self, v):
        self.pos[1] = v
        return

    def z(self, v):
        self.pos[2] = v
        return

    def __repr__(self):
        print(self.__str__())
        return

    def __str__(self):
        s = f"({self.pos[0, 0]},{self.pos[1, 0]},{self.pos[2, 0]})"
        return s


class attitude:
    """
    attitude by DCM
    """

    def __init__(self, rx=0, ry=0, rz=0):
        self._reset()
        self.eulaRotate(rx, ry, rz)
        return

    def _reset(self):
        self.DCM = np.matrix(np.eye(3))
        return

    def __normalized(self):
        # use gram schmidt
        matrix = self.DCM
        for i in range(1, 3):
            matrix[:, i] /= np.linalg.norm(matrix[:, i])

        self.DCM = matrix
        return

    def eulaRotate(self, x, y, z, order="XYZ"):
        assert type(order) is str, "order must be str type"
        assert len(order) == 3, "order len must be 3"
        order = order.upper()
        assert all(c in {'X', 'Y', 'Z'} for c in order), "order string only can contain 'X', 'Y', or 'Z'"

        for i in range(0, 3):
            rotateType = order[i]
            if rotateType == "X":
                self._rotateX(x)
            elif rotateType == "Y":
                self._rotateY(y)
            else:  # rotateType=="Z":
                self._rotateZ(z)

        self.__normalized()
        return

    def _rotateX(self, arg):
        cosArg = np.cos(arg)
        sinArg = np.sin(arg)
        rotate = np.matrix(np.zeros(shape=(3, 3)))

        rotate[0, 0] = 1
        rotate[0, 1] = 0
        rotate[0, 2] = 0

        rotate[1, 0] = 0
        rotate[1, 1] = cosArg
        rotate[1, 2] = -sinArg

        rotate[2, 0] = 0
        rotate[2, 1] = sinArg
        rotate[2, 2] = cosArg

        self.DCM = rotate * self.DCM
        return

    def _rotateY(self, arg):
        cosArg = np.cos(arg)
        sinArg = np.sin(arg)
        rotate = np.matrix(np.zeros(shape=(3, 3)))

        rotate[0, 0] = cosArg
        rotate[0, 1] = 0
        rotate[0, 2] = sinArg

        rotate[1, 0] = 0
        rotate[1, 1] = 1
        rotate[1, 2] = 0

        rotate[2, 0] = -sinArg
        rotate[2, 1] = 0
        rotate[2, 2] = cosArg

        self.DCM = rotate * self.DCM
        return

    def _rotateZ(self, arg):
        cosArg = np.cos(arg)
        sinArg = np.sin(arg)
        rotate = np.matrix(np.zeros(shape=(3, 3)))

        rotate[0, 0] = cosArg
        rotate[0, 1] = -sinArg
        rotate[0, 2] = 0

        rotate[1, 0] = sinArg
        rotate[1, 1] = cosArg
        rotate[1, 2] = 0

        rotate[2, 0] = 0
        rotate[2, 1] = 0
        rotate[2, 2] = 1

        self.DCM = rotate * self.DCM
        return

    def __debug_print_matrix(self, m):
        s = ""
        for c in range(0, 3):
            for r in range(0, 3):
                s += "%10.3f" % (m[r, c])
            s += "\n"
        return s

    def __repr__(self):
        print(self.__debug_print_matrix(self.DCM))
        return

    def __str__(self):
        s = self.__debug_print_matrix(self.DCM)
        return s

    def __copy__(self):
        state = np.matrix(self.DCM)
        newCopy = type(self)().DCM = state
        return newCopy


class sunset:
    def __init__(self):
        self.earthLocation = location()
        self.earthAttitude = attitude()
        self.viewPositionOnEarth = attitude()
        return

    def setViewPositionOnEarth(self, latitude, longitude):
        """

        :param latitude: unit is deg. North is negetive, Sorth is positive, e.g. 40N->40 45S->-45
        :param longitude: unit is deg. East is negetive, West is positive.
        :return: None
        """
        self.viewPositionOnEarth = attitude()
        self.viewPositionOnEarth.eulaRotate(math.radians(longitude), math.radians(latitude), 0, order='zyx')
        logger.debug(f"position on earth lat,lon:({latitude},{longitude})")
        logger.debug(f"position on earth DCM:\n{self.viewPositionOnEarth}")
        return

    def _earthRotate(self, rad):
        attitudeAtTime = attitude()
        attitudeAtTime.eulaRotate(0, 0, rad)
        attitudeAtTime = attitudeAtTime.DCM * self.viewPositionOnEarth.DCM

        earthTilt = attitude()
        earthTilt.eulaRotate(0, nature_const.earthTilt, 0, order="zyx")

        result = earthTilt.DCM * attitudeAtTime
        return result

    def _earthLocation(self, rad):
        earth_sun_attitude = attitude()
        earth_sun_attitude.eulaRotate(0, 0, rad)
        # logger.debug(f"earth-sun location attitude\n {earth_sun_attitude}")

        beginLocation = np.matrix(np.zeros(shape=(3, 1)))
        beginLocation[0] = nature_const.sun2earth
        earthLocation = earth_sun_attitude.DCM * beginLocation
        # logger.debug(f"earth-sun location\n {earthLocation} km")
        return earthLocation

    def sunAngle(self, dayOfYear, leapYear=False):
        """

        :param dayOfYear:
        :param leapYear:
        :return:
        """
        _yearPeriod = 365
        _earthRotationRadPerDay = (2 * np.pi) / _yearPeriod + (2 * np.pi)

        if leapYear == True:
            _yearPeriod = 366
        sun2earthAngle = dayOfYear / _yearPeriod * 2 * np.pi
        sunLocationRelative2Earth = -self._earthLocation(sun2earthAngle)
        sunLocationRelative2Earth /= np.linalg.norm(sunLocationRelative2Earth)
        # logger.debug(f"sun location on earth \n {sunLocationRelative2Earth}")

        DAY_PRECISION = 60 * 60 * 24
        # dayAngle = (int(dayOfYear * DAY_PRECISION) % DAY_PRECISION) / DAY_PRECISION * 2 * np.pi
        dayAngle = dayOfYear * _earthRotationRadPerDay
        # logger.debug(f"dayOfYear {dayOfYear} timeOfday {(int(dayOfYear * DAY_PRECISION) % DAY_PRECISION) / DAY_PRECISION}")
        skyVector = self._earthRotate(dayAngle)[:, 0]
        # logger.debug(f"sky vector \n {skyVector}")

        cosineAngle = (sunLocationRelative2Earth.T * skyVector) / (np.linalg.norm(sunLocationRelative2Earth) * np.linalg.norm(skyVector))
        radAngle = np.arccos(np.clip(cosineAngle, -1, 1))[0, 0]
        angle = math.degrees(radAngle)
        # logger.debug(f"sun angle \n {math.degrees(angle)}")
        return angle


def main(argConfigure) -> None:
    logger.info(f"sun to earth distance {nature_const.sun2earth / 1000}km")
    a = location()
    b = location(1)
    logger.info(f"location test {a + b}")
    ss = sunset()
    ss.setViewPositionOnEarth(34.27, 108.93)
    ss._earthRotate(np.pi / 6)
    ss._earthLocation(np.pi / 6)
    ss.sunAngle(100.5012)

    # debug

    import matplotlib.pyplot as plt

    dayofyearArray = np.linspace(0, 2, 60 * 60 * 24 * 2)
    sunAngleArray = np.zeros_like(dayofyearArray)
    for idx, v in enumerate(dayofyearArray):
        if idx % (60 * 60 * 1) == 0:
            logger.debug(f"idx:{idx} day of year:{v}")
        sunAngleArray[idx] = ss.sunAngle(v)

    plt.plot(dayofyearArray, sunAngleArray)
    plt.title('sun angle at sky')
    plt.show()

    dayofyearArray = [v + 0.5 for v in range(0, 365)]
    sunAngleArray = np.zeros_like(dayofyearArray)
    for idx, v in enumerate(dayofyearArray):
        logger.debug(f"idx:{idx} day of year:{v}")
        sunAngleArray[idx] = ss.sunAngle(v)

    plt.plot(dayofyearArray, sunAngleArray)
    plt.title('sun angle at sky')
    plt.show()

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
        self.tableName = "execute-" + datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
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
        cmd = cmd + columnStr + " VALUES " + bindValueStr
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
        console_handler.setLevel(logging.DEBUG)
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
# create by base python script creator 0.4.0
# create on  [+0800]2024-05-18 00:26:54
