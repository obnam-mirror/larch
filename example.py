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


import hashlib
import os
import sys

import btree


def compute(filename):
    f = open(filename)
    md5 = hashlib.md5()
    while True:
        data = f.read(1024)
        if not data:
            break
        md5.update(data)
    f.close()
    return md5.hexdigest()


def open_tree(dirname):
    key_size = len(compute('/dev/null'))
    node_size = 4096
    
    codec = btree.NodeCodec(key_size)
    ns = btree.NodeStoreDisk(node_size, codec, dirname=dirname)
    forest = btree.Forest(ns)
    if forest.trees:
        tree = forest.trees[0]
    else:
        tree = forest.new_tree()
    return forest, tree


def add(filenames):
    forest, tree = open_tree('example.tree')
    for filename in filenames:
        checksum = compute(filename)
        tree.insert(checksum, filename)
    forest.commit()


def find(checksums):
    forest, tree = open_tree('example.tree')
    for checksum in checksums:
        filename = tree.lookup(checksum)
        print checksum, filename


def list_checksums():
    forest, tree = open_tree('example.tree')
    key_size = len(compute('/dev/null'))
    minkey = '00' * key_size
    maxkey = 'ff' * key_size
    for checksum, filename in tree.lookup_range(minkey, maxkey):
        print checksum, filename


def main():
    if sys.argv[1] == 'add':
        add(sys.argv[2:])
    elif sys.argv[1] == 'find':
        find(sys.argv[2:])
    elif sys.argv[1] == 'list':
        list_checksums()
    else:
        raise Exception('Unknown operation %s' % sys.argv[1])


if __name__ == '__main__':
    main()
