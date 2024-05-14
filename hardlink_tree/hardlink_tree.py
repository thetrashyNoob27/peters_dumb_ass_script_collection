#!/usr/bin/env python3
import os
import sys
import argparse

def is_path_inside(parent_path, child_path):
    common_prefix = os.path.commonprefix([parent_path, child_path])
    return common_prefix == parent_path

def hardlink_dir(src,dst):
    DEBUG=False
    make_folder_list=[]
    link_file_list=[]
    for root, dirs, files in os.walk(src, topdown=True):
        if is_path_inside(root,src) and root!=src:
            continue
        
        
        for folder in dirs:
            full_path=root+os.sep+folder
            if is_path_inside(full_path,src):
                continue
            dst_path=dst+os.sep+os.path.relpath(root,src)+os.sep+folder
            if dst_path not in make_folder_list:
                make_folder_list.append(dst_path)
            if DEBUG:
                print("src_dir:"+full_path)
                print("make_dir:"+dst_path)
                print()
        for file in files:
            full_path=root+os.sep+file
            if is_path_inside(full_path,src):
                continue
            dst_path=dst+os.sep+os.path.relpath(root,src)+os.sep+file
            link_file_list.append((full_path,dst_path))
            if DEBUG:
                print("src_file:"+full_path)
                print("link_file:"+dst_path)
                print()
                
    if not DEBUG:
        for folder in make_folder_list:
            os.makedirs(folder,exist_ok=True)
        for file in link_file_list:
            src,dst=file
            try:
                os.link(src,dst)
            except FileExistsError as e:
                print("file:%s exists." %(dst))
                pass
            except FileNotFoundError as e:
                print("file:%s no found" %(dst))
                

if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('src', help='source file/directory')
    parser.add_argument('dst', help='destination file/directory')
    args = parser.parse_args()
    
    src=args.src
    dst=args.dst
    src=os.path.realpath(src)
    dst=os.path.realpath(dst)

    if not os.path.exists(src):
        print("src path not exist")
        sys.exit(2)
    if src==dst:
        print("src==dst")
        sys.exit(3)
    hardlink_dir(src,dst)