#!/usr/bin/env python3
import base64
import os
_EOF_ = ""
_EOF_ += "__"
_EOF_ += "EOF"
_EOF_ += "__"


def reduce_paths(paths):
    parent_dirs = set()
    for path in paths:
        parts = path.split('/')
        for i in range(1, len(parts)):
            parent_dirs.add('/'.join(parts[:i]))
    reduced_paths = [path for path in paths if path not in parent_dirs]

    return reduced_paths


if __name__ == "__main__":
    folderList = []
    fileList = []
    relativePath = os.path.dirname(os.getcwd())
    createRoot = os.path.basename(os.getcwd())

    for root, dirs, files in os.walk(os.getcwd()):
        for file in files:
            filePath = os.path.join(root, file)
            fileList.append(filePath)
        for directory in dirs:
            dirPath = os.path.join(root, directory)
            folderList.append(dirPath)

    folderList = reduce_paths(folderList)

    # mkdir bash
    scriptStr = []
    print("#make paths")
    for f in folderList:
        createPath = os.path.relpath(f, relativePath)
        cmd = "mkdir -pv \"%s\"" % (createPath)
        scriptStr.append(cmd)

    print("#make cat EOF")
    for f in fileList:
        if os.path.islink(f):
            continue
        notTextFile = False
        createPath = os.path.relpath(f, relativePath)
        with open(f, 'r') as fd:
            try:
                text = fd.read()
            except UnicodeDecodeError as e:
                notTextFile = True
                createPath64 = createPath+".base64"
        if notTextFile:
            with open(f, 'rb') as fd:
                data = fd.read()
                b64data = base64.b64encode(data).decode()

        if not notTextFile:
            cmd = "cat<<'%s' >\"%s\"" % (_EOF_, createPath)
        else:
            cmd = "cat<<'%s' >\"%s\"" % (_EOF_, createPath64)
        cmd += "\n"
        if not notTextFile:
            cmd += text
        else:
            cmd += b64data
        cmd += "\n"
        cmd += "%s" % (_EOF_)
        cmd += "\n"
        if notTextFile:
            cmd += "cat \"%s\" | base64 -d > \"%s\"\n" % (
                createPath64, createPath)
            cmd += "rm \"%s\"\n" % (createPath64)
        fileMode = '0' + format(os.stat(f).st_mode % 512, 'o')
        cmd += "chmod %s \"%s\"" % (fileMode, createPath)
        scriptStr.append(cmd)
        scriptStr.append("\n")

    for cmd in scriptStr:
        print(cmd)

    scriptPath = "/tmp/cat_EOF_create_script_%s.txt" % (createRoot)
    with open(scriptPath, 'w') as f:
        f.write("#!/usr/bin/bash\n")
        for cmd in scriptStr:
            f.write(cmd)
            f.write("\n")
    os.chmod(scriptPath, os.stat(scriptPath).st_mode | 0o111)
