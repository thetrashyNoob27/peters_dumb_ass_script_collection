#!/usr/bin/env python3

import re
import shlex
import subprocess
import sqlite3
import socket
import datetime
import argparse
import os

def listTorrents(server="192.168.16.6:9091"):
    command = shlex.split("transmission-remote %s -l" % (server))
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    resultLines=result.stdout.split('\n')

    recordList = []

    headerLine = resultLines[0]
    splitIndex = []
    headerNames = [h for h in headerLine.split(' ') if len(h) > 0]
    splitIndex = [headerLine.find(h) + len(h) for h in headerNames]
    recordLine = resultLines[1:-2]


    for r in recordLine:
        rowInfo = {}
        lastIndex = 0
        for idx, name in enumerate(headerNames):
            split = splitIndex[idx]
            if name == 'Name':
                subStr = r[split - len('Name'):].strip()
            elif name == "Status":
                subStr = r[split - len('Status'):splitIndex[idx + 1] - len(headerNames[idx + 1])].strip()
            elif name == "ETA":
                endIndex = -1
                for i in range(splitIndex[idx + 1] - 1, split, -1):
                    endIndex = i
                    if r[i] == ' ':
                        break
                subStr = r[split - len('ETA'):endIndex].strip()
                split = endIndex
            else:
                subStr = r[lastIndex:split].strip()

            rowInfo[name] = subStr
            lastIndex = split
        recordList.append(rowInfo)


    return recordList


def dumpTorrentInfo(server="192.168.16.6:9091"):
    records = listTorrents(server)
    for t in records:
        command = shlex.split("transmission-remote %s -t %s --info" % (server, t['ID']))
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        t['info'] = result.stdout
        magnetRe = re.compile("  Magnet: (.+)\n")
        t['magnet'] = magnetRe.findall(result.stdout)[0]
        addDateRe = re.compile("Date added:\s+(.+)\n")
        t['date'] = addDateRe.findall(result.stdout)[0]
        parsedDatetime = datetime.datetime.strptime(t['date'], "%a %b %d %H:%M:%S %Y")
        t['date'] = parsedDatetime.strftime("%Y-%m-%d %H:%M:%S")

    return records


def makeMarkdown(records):
    mdRecord = []
    for r in records:
        nameRe = re.compile("  Name: (.+)\n")
        magnetRe = re.compile("  Magnet: (.+)\n")
        name = nameRe.findall(r['info'])[0]
        magnet = magnetRe.findall(r['info'])[0]
        mdLink = "[%s](%s)" % (name, magnet)
        mdRecord.append(mdLink)
    return mdRecord


class torrentDb:
    def __init__(self, name=None):
        if name is not None:
            self.dbName = name
        else:
            scriptPath = os.path.dirname(__file__)
            self.dbName=scriptPath+os.sep+"torrent.sqlite3"
        self.db = sqlite3.connect(self.dbName)
        self._databaseSetup()
        self._updateMagnetDate()
        return

    def __def__(self):
        self.db.close()
        return

    def _databaseSetup(self):
        cur = self.db.cursor()
        for cmd in self._databaseConstructCMD():
            cur.execute(cmd)
        return

    def _databaseConstructCMD(self):
        cmdList = []
        cmdList.append("""CREATE TABLE IF NOT EXISTS "magnet" (
	"name"	TEXT,
	"date"	TEXT,
	"size"	TEXT,
	"link"	TEXT UNIQUE
);""")
        cmdList.append("""CREATE TABLE  IF NOT EXISTS "log" (
	"id"	INTEGER NOT NULL UNIQUE,
	"executeHost"	TEXT,
	"date"	TEXT,
	"dumpHost" TEXT,
	PRIMARY KEY("id" AUTOINCREMENT)
);""")
        return cmdList

    def getCurscur(self):
        return self.db.cursor()

    def insertLog(self, dumpHost):
        hostname = socket.gethostname()
        datestr = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = self.getCurscur()
        cur.execute("""INSERT INTO "log" ("executeHost","date","dumpHost") VALUES (?,?,?)""",
                    (hostname, datestr, dumpHost))
        return

    def insertRecord(self, name, date, size, link):
        cur = self.getCurscur()
        data = (name, date, size, link)
        try:
            cur.execute("""INSERT INTO magnet ("name","date","size","link") VALUES (?,?,?,?)""", data)
        except sqlite3.IntegrityError as e:
            cur.execute("""UPDATE magnet SET "size" = ? WHERE "link" = ?""", (size,link))
        finally:
            self.db.commit()
        return

    def getTableColumnName(self, table):
        table_name = "people"  # Replace with your table name
        cur = self.db.cursor()
        cur.execute(f"PRAGMA table_info({table})")
        columns = cur.fetchall()
        column_names = [column[1] for column in columns]
        return column_names

    def getMagnetRecords(self):
        cur = self.getCurscur()
        cur.execute("""SELECT * FROM 'magnet' ORDER BY 'name'""")
        columnName = self.getTableColumnName('magnet')
        magnetRecords = []
        for row in cur.fetchall():
            record = dict(zip(columnName, row))
            magnetRecords.append(record)
        return magnetRecords

    def _updateMagnetDate(self):
        records=self.getMagnetRecords()
        cur = self.getCurscur()
        for r in records:
            try:
                parsedDatetime = datetime.datetime.strptime(r['date'], "%a %b %d %H:%M:%S %Y")
            except ValueError as err:
                continue
            r['date'] = parsedDatetime.strftime("%Y-%m-%d %H:%M:%S")
            cur.execute("""UPDATE magnet SET "date" = ? WHERE "link" = ?""", (r['date'],r['link']))
        self.db.commit()


def makeArgProcesser():
    parser = argparse.ArgumentParser(description='dump transmission torrents')
    parser.add_argument('-s', '--server', default='localhost:9091', help='Server address (default: localhost:9091)')
    parser.add_argument('-m', '--markdown', action='store_true', help='Export as markdown')

    return parser.parse_args()


# Press the green button in the gutter to run the script.
if __name__ == '__main__':

    arg=makeArgProcesser()
    querryHost = arg.server
    records = dumpTorrentInfo(querryHost)

    #db path
    dbPath=os.path.expanduser('~/.local/var/lib')
    os.makedirs(dbPath,exist_ok=True)

    db = torrentDb(dbPath+os.sep+"transmission-torrents.sqlite3")
    db.insertLog(querryHost)
    for l in records:
        db.insertRecord(l['Name'], l['date'], l['Have'], l['magnet'])

    if arg.markdown :
        for r in db.getMagnetRecords():
            print("[%s](%s)" %(r['name'],r['link']))