#!/usr/bin/env python3
import base64
import sys
import os
import argparse


def argprase():
    parser = argparse.ArgumentParser(description="Description of your program")

    # Define options
    parser.add_argument("--force-base64", dest="force_base64",
                        action="store_true", help="force file use base64")
    parser.add_argument("-b", "--base", dest="base_path",
                        default=None, help="Base path")
    parser.add_argument("-i", "--include", dest="include_paths", action="append",
                        default=[], help="Include path (can be defined multiple times)")

    # Parse the command-line arguments
    args = parser.parse_args()
    if args.base_path is None:
        args.base_path = "../"

    if len(args.include_paths) == 0:
        args.include_paths.append(os.getcwd())

    # logic check
    # args.base_path = os.path.realpath(args.base_path)
    # for idx, path in enumerate(args.include_paths):
    #     args.include_paths[idx] = os.path.realpath(path)

    if not os.path.exists(args.base_path):
        print("base path invalid")
        sys.exit()
    for idx, path in enumerate(args.include_paths):
        if os.path.exists(path):
            continue
        print("include path: \"%s\" invalid" % (path))
        sys.exit()

    def is_parent(parent, child):
        real_parent = os.path.relpath(parent, "/")
        real_child = os.path.relpath(child, "/")
        common_path = os.path.commonpath([real_parent, real_child])
        return common_path == real_parent
    for idx, path in enumerate(args.include_paths):
        if is_parent(args.base_path, path):
            continue
        continue  # need fix this
        print("include: %s is not sub-path of base: %s" %
              (path, args.base_path))
        sys.exit()

    return args


def reduce_paths(paths):
    parent_dirs = set()
    for path in paths:
        parts = path.split('/')
        for i in range(1, len(parts)):
            parent_dirs.add('/'.join(parts[:i]))
    reduced_paths = [path for path in paths if path not in parent_dirs]

    return reduced_paths


def folders2mkdir(dirs):
    cmdList = []
    for f in dirs:
        cmd = "mkdir -pv \"%s\"" % (f)
        cmdList.append(cmd)
    return cmdList


def file2heredocument(path, createBase, force_base64=False):

    _EOF_ = ""
    _EOF_ += "__"
    _EOF_ += "EOF"
    _EOF_ += "__"
    createPath = os.path.relpath(path, createBase)

    with open(path, 'rb') as fd:
        content = fd.read()
    try:
        content = content.decode()
        notTextFile = False
    except UnicodeDecodeError as e:
        notTextFile = True
    if notTextFile or force_base64:
        createPath64 = createPath+".base64"
        content = base64.b64encode(content).decode()
    else:
        pass

    cmd = str()
    if notTextFile or force_base64:
        cmd = "cat<<'%s' >\"%s\"" % (_EOF_, createPath64)
    else:
        cmd = "cat<<'%s' >\"%s\"" % (_EOF_, createPath)
    cmd += "\n"
    if not notTextFile:
        cmd += content
    else:
        cmd += content
    cmd += "\n"
    cmd += "%s" % (_EOF_)
    cmd += "\n"
    if notTextFile:
        cmd += "cat \"%s\" | base64 -d > \"%s\"\n" % (
            createPath64, createPath)
        cmd += "rm \"%s\"\n" % (createPath64)
    fileMode = '0' + format(os.stat(f).st_mode % 4096, 'o')
    cmd += "chmod %s \"%s\"" % (fileMode, createPath)
    return cmd


def elementDiscovery(include_path):
    folderList = []
    fileList = []
    createBase = os.path.basename(os.path.realpath(parms.base_path))
    if os.path.isdir(include_path):
        folderList.append(include_path)
    else:
        fileList.append(include_path)

    for root, dirs, files in os.walk(include_path):
        for file in files:
            filePath = os.path.join(root, file)
            fileList.append(filePath)
        for directory in dirs:
            dirPath = os.path.join(root, directory)
            folderList.append(dirPath)

    folderList = reduce_paths(folderList)
    return folderList, fileList


if __name__ == "__main__":
    parms = argprase()

    for include_path in parms.include_paths:
        include_path = os.path.realpath(include_path)
        createBase = "./"
        basePath = os.path.realpath(parms.base_path)
        if include_path != os.path.realpath(basePath):
            createBase = os.path.basename(os.path.realpath(basePath))
        folderList, fileList = elementDiscovery(include_path)
        for idx, path in enumerate(folderList):
            folderList[idx] = os.path.relpath(
                path, os.path.realpath(basePath))
        # mkdir bash
        scriptStr = folders2mkdir(folderList)
        for f in fileList:
            if os.path.islink(f):
                continue

            cmd = file2heredocument(f, basePath)
            scriptStr.append(cmd)

        for cmd in scriptStr:
            print(cmd)

        scriptPath = "/tmp/cat_EOF_create_script_%s.txt" % (
            os.path.dirname(createBase))
        with open(scriptPath, 'w') as f:
            f.write("#!/usr/bin/bash\n")
            for cmd in scriptStr:
                f.write(cmd)
                f.write("\n")
        os.chmod(scriptPath, os.stat(scriptPath).st_mode | 0o111)
