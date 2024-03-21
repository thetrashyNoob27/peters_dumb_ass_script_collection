#!/usr/bin/env python3
import os
import sys
import re
import csv


def _read_acf(acf_path):
    with open(acf_path, 'r') as f:
        text = f.read()
    lines = text.split("\n")
    app_name_re = re.compile(r"\"name\".+\"(.+)\"")
    for l in lines:
        finds = re.findall(app_name_re, l)
        if len(finds) != 1:
            continue
        return finds[0]


def read_acf_files(acfs):
    for info in acfs:
        info["name"] = _read_acf(info["path"])
    return


def find_steam_acf(search_path):
    acf_files = []
    steam_acf_name_pattern = re.compile(r"appmanifest_(\d+)\.acf")
    for root, dirs, files in os.walk(search_path):
        for file in files:
            match_result = re.findall(steam_acf_name_pattern, file)
            if len(match_result) == 0:
                continue
            match_result = match_result[0]
            acf_files.append(
                {"id": match_result, "path": os.path.join(root, file)})
    read_acf_files(acf_files)
    return acf_files


def find_proton_drive_c(search_path):
    proton_c = []
    steam_acf_name_pattern = re.compile(r"appmanifest_(\d+)\.acf")
    for root, dirs, files in os.walk(search_path):
        if "drive_c" not in dirs:
            continue
        path_info = root.split("/")
        if path_info[-3] != "compatdata" or path_info[-1] != "pfx":
            continue
        app_id = path_info[-2]
        proton_c.append({"id": app_id, "path": root})
    return proton_c


def find_steam_app_info(search_path):
    acfs = find_steam_acf(search_path)
    proton_c = find_proton_drive_c(search_path)
    steam_game_info = {}
    for info in acfs:
        app_id = int(info["id"])
        if app_id not in steam_game_info.keys():
            steam_game_info[app_id] = {}
        steam_game_info[app_id]["acf_path"] = info["path"]
        steam_game_info[app_id]["name"] = info["name"]

    for info in proton_c:
        app_id = int(info["id"])
        if app_id not in steam_game_info.keys():
            steam_game_info[app_id] = {}
        steam_game_info[app_id]["proton_c_path"] = info["path"]

    remove_keys = []
    for k, v in steam_game_info.items():
        for must_key in ['acf_path', 'proton_c_path', 'name']:
            if must_key not in v.keys():
                remove_keys.append(k)
                break
    for k in remove_keys:
        del steam_game_info[k]

    return steam_game_info


def find_steam_library_path():
    libraryLogFile = "~/.local/share/Steam/config/libraryfolders.vdf"
    libraryLogFile = os.path.expanduser(libraryLogFile)

    with open(libraryLogFile, 'r') as f:
        steamLibraryVdf = f.read()
    path_re = re.compile(r"\"path\".+\"(.+)\"")
    libraryPathList = re.findall(path_re, steamLibraryVdf)
    return libraryPathList


def escape_invalid_characters(filename):
    # Define a regular expression pattern to match characters not allowed in file names
    invalid_chars_pattern = r'[<>:"/\\|?*\x00-\x1F\']'

    # Replace invalid characters with an underscore
    escaped_filename = re.sub(invalid_chars_pattern, ' ', filename)

    return escaped_filename


if __name__ == "__main__":
    steamLibraryPathList = find_steam_library_path()
    steam_game_info = {}
    for p in steamLibraryPathList:
        print("prasing library:%s" % (p))
        game_infos = find_steam_app_info(os.path.join(p, "steamapps"))
        steam_game_info.update(game_infos)

    proton_c_links_path = libraryLogFile = os.path.expanduser("~")
    proton_c_links_path = os.path.join(proton_c_links_path, "proton_c_drive")
    os.makedirs(proton_c_links_path, exist_ok=True)
    for appid, appinfo in steam_game_info.items():
        if "proton_c_path" not in appinfo.keys() or "name" not in appinfo.keys():
            # print("game id:%d ,missing info (%s)" %(appid,appinfo.__str__()))
            continue
        try:
            os.symlink(os.path.join(appinfo["proton_c_path"], 'drive_c'), os.path.join(
                proton_c_links_path, escape_invalid_characters("[%d] " % (appid)+appinfo["name"])))
        except FileExistsError as e:
            pass
