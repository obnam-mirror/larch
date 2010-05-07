#!/usr/bin/python


import os
import cProfile
import pstats
import random
import shutil
import sys
import tempfile
import time
import uuid

import btree


def measure(keys, func):
    start = time.clock()
    for key in keys:
        func(key)
    end = time.clock()
    return end - start


def generate_keys(key_size):
    while True:
        u = uuid.uuid4()
        mainkey = u.bytes[:9]
        subkey = u.bytes[-9:]
        for subtype in range(4):
            yield '%s%c%s' % (mainkey, subtype, subkey)


def main():
    n = int(sys.argv[1])

    key_size = 19
    value_size = 128
    node_size = 64*1024

    location = tempfile.mkdtemp()

    codec = btree.NodeCodec(key_size)
    if True:
        ns = btree.NodeStoreMemory(node_size, codec)
    else:
        ns = btree.NodeStoreDisk(location, node_size, codec)
    forest = btree.Forest(ns)
    tree = forest.new_tree()

    keys = [key for i, key in zip(xrange(n), generate_keys(key_size))]
    
    random.shuffle(keys)
    value = 'x' * value_size
    measure(keys, lambda key: tree.insert(key, value))

    if location:
        shutil.rmtree(location)

if __name__ == '__main__':
    cProfile.run('main()', 'insert.prof')

