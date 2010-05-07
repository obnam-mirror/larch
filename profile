#!/usr/bin/python
# Copyright 2010  Lars Wirzenius
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


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

