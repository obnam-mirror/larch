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


import logging
import sys

import btree


def assert_equal(a, b, msg=''):
    if a != b:
        if msg:
            logging.error(msg)
        logging.error('not true: %s == %s' % (repr(a), repr(b)))


def assert_greater(a, b, msg=''):
    if a <= b:
        if msg:
            logging.error(msg)
        logging.error('not true: %s > %s' % (repr(a), repr(b)))
            
            
def check_index_node(ns, node_id):
    logging.info('checking index node: %d' % node_id)
    node = ns.get_node(node_id)
    assert_greater(ns.get_refcount(node_id), 0, 'node refcount should be > 0')


def check_root_node(ns, root_id):
    logging.info('checking root node: %d' % root_id)
    root = ns.get_node(root_id)
    assert_equal(ns.get_refcount(root_id), 1, 'root refcount should be 1')
    

def check_tree(ns, root_id):
    logging.info('checking tree: %d' % root_id)
    check_root_node(ns, root_id)
    check_index_node(ns, root_id)


def forest_root_ids(ns):
    string = ns.get_metadata('root_ids')
    return [int(x) for x in string.split(',')]


def check_forest(ns):
    for root_id in forest_root_ids(ns):
        check_tree(ns, root_id)


def main():
    dirname = sys.argv[1]
    node_size = int(sys.argv[2])
    key_size = int(sys.argv[3])
    
    logging.basicConfig(stream=sys.stdout, format='%(levelname)s: %(message)s', 
                        level=logging.DEBUG)
    logging.info('btree fsck')
    logging.info('forest: %s' % dirname)
    logging.info('node size: %d' % node_size)
    logging.info('key size: %d' % key_size)

    codec = btree.NodeCodec(key_size)
    ns = btree.NodeStoreDisk(dirname, node_size, codec)
    check_forest(ns)


if __name__ == '__main__':
    main()
