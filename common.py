#!/usr/bin/env python3
import os.path

def file_in_this_dir(name):
    return os.path.join(os.path.dirname(__file__), name)

NODE_LIST_TXT = file_in_this_dir("Node List.txt")
