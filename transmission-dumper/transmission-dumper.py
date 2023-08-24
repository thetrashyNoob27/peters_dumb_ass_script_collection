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

    torrentListRe = re.compile(r'(\d+)\s+(\d+)\%\s+(.+B)\s+([^ ]+)\s+([^ ]+)\s+([^ ]+)\s+([^ ]+)\s+([^ ]+)\s+([^ ]+)\n')
    torrentRecords = torrentListRe.findall(result.stdout)

    recordList = []

    for rec in torrentRecords:
        row = {}
        #    ID   Done       Have  ETA           Up    Down  Ratio  Status       Name
        _idx = 0
        row['ID'] = int(rec[_idx])
        _idx += 1
        row['Done'] = rec[_idx]
        _idx += 1
        row['Have'] = rec[_idx]
        _idx += 1
        row['ETA'] = rec[_idx]
        _idx += 1
        row['Up'] = rec[_idx]
        _idx += 1
        row['Down'] = rec[_idx]
        _idx += 1
        row['Ratio'] = rec[_idx]
        _idx += 1
        row['Status'] = rec[_idx]
        _idx += 1
        row['Name'] = rec[_idx]
        _idx += 1
        del _idx

        recordList.append(row)
    return recordList


def dumpTorrentInfo(server="192.168.16.6:9091"):
    records = listTorrents(server)
    for t in records:
        command = shlex.split("transmission-remote %s -t %d --info" % (server, t['ID']))
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        t['info'] = result.stdout
        magnetRe = re.compile("  Magnet: (.+)\n")
        t['magnet'] = magnetRe.findall(result.stdout)[0]
        addDateRe = re.compile("Date added:\s+(.+)\n")
        t['date'] = addDateRe.findall(result.stdout)[0]

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
            cur.execute("""INSERT INTO magnet ('name','date','size','link') VALUES (?,?,?,?)""", data)
        except sqlite3.IntegrityError as e:
            pass
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
    db = torrentDb()
    db.insertLog(querryHost)
    for l in records:
        db.insertRecord(l['Name'], l['date'], l['Have'], l['magnet'])

    if arg.markdown :
        for r in db.getMagnetRecords():
            print("[%s](%s)" %(r['name'],r['link']))