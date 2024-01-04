#!/usr/bin/env python3
import argparse
import sys
import os
import errno
import shutil


def pathTree(path):
    dirTree = []
    fileTree = []
    for root, dirs, files in os.walk(path, topdown=False):
        fileTree.extend([os.path.join(root, f) for f in files])
        dirTree.extend([os.path.join(root, d) for d in dirs])
    return dirTree, fileTree


def andPaths(src, dst):
    src = set(src)
    deleteList = []
    for dObj in dst:
        if dObj in src:
            deleteList.append(dObj)
    return deleteList


def getRelPathList(paths, basepath):
    return [os.path.relpath(p, basepath) for p in paths]


def nandFiles(srcFiles, srcBase, dstFiles, dstBase):
    srcRelFiles = getRelPathList(srcFiles, srcBase)
    dstRelFiles = getRelPathList(dstFiles, dstBase)
    trueFiles = andPaths(srcRelFiles, dstRelFiles)
    delList = []
    for f in trueFiles:
        p = dstBase+os.sep+f
        if os.path.isdir(p):
            p += os.sep
            try:
                os.rmdir(p)
            except OSError as e:
                if e.errno == errno.ENOTEMPTY or e.errno == errno.EEXIST:
                    print("path %s not empty. not removing." % (p))
                else:
                    print("un-foreseen error, not delete any way:%s(%s)" % (p, e))
                continue
        else:
            os.remove(p)
        delList.append(p)
    return delList


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="and logic file remover.")

    # Add optional arguments
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable verbose mode")

    # Add positional arguments
    parser.add_argument("src_path", help="Source path")
    parser.add_argument("dst_path", help="Destination path")

    # Parse the command-line arguments
    args = parser.parse_args()

    srcPath = args.src_path
    dstPath = args.dst_path
    if not os.path.isdir(srcPath):
        print("src path is not exist.")
        sys.exit(1)
    if not os.path.isdir(dstPath):
        print("dst path is not exist.")
        sys.exit(1)
    if os.path.samefile(srcPath, dstPath):
        print("src dst same.")
        sys.exit(1)

    if args.verbose:
        print("src path: %s" % (srcPath))
        print("dst path: %s" % (dstPath))

    srcDirs, srcFiles = pathTree(srcPath)
    dstDirs, dstFiles = pathTree(dstPath)

    delFiles = nandFiles(srcFiles, srcPath, dstFiles, dstPath)

    delDirs = nandFiles(srcDirs, srcPath, dstDirs, dstPath)
    if args.verbose:
        for p in delFiles:
            print(p)
        for p in delDirs:
            print(p)
