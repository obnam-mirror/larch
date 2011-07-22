# Copyright 2010, 2011  Lars Wirzenius
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
import ttystatus

import larch


class Error(Exception):

    def __init__(self, msg):
        self.msg = 'Assertion failed: %s' % msg
        
    def __str__(self):
        return self.msg


class WorkItem(object):

    '''A work item for fsck.'''

    def __str__(self):
        return self.name
    
    def do(self):
        pass

    def error(self, msg):
        self.fsck.report('%s: %s' % (self.name, msg))

    def get_node(self, node_id):
        try:
            return self.fsck.forest.node_store.get_node(node_id)
        except larch.NodeMissing:
            self.error('node %s is missing' % node_id)


class CheckNode(WorkItem):

    def __init__(self, fsck, node_id):
        self.fsck = fsck
        self.node_id = node_id
        self.name = 'node %s' % node_id

    def do(self):
        node = self.get_node(self.node_id)
        if node:
            if type(node) not in [larch.IndexNode, larch.LeafNode]:
                self.error('node must be an index or leaf node')
                return
            keys = node.keys()
            if self.fsck.forest.node_store.get_refcount(node.id) <= 0:
                self.error('node refcount must be > 0')
            if not len(keys):
                self.error('node must have keys')
            if sorted(keys) != keys:
                self.error('node keys must be sorted')
            if sorted(set(keys)) != keys:
                self.error('node keys must be unique')
            encoded = self.fsck.forest.node_store.codec.encode(node)
            if len(encoded) > self.fsck.forest.node_store.node_size:
                self.error('node is too large')
            if len(encoded) == 0:
                self.error('node has zero size when encoded')


class CheckRoot(WorkItem):

    def __init__(self, fsck, root_id):
        self.fsck = fsck
        self.root_id = root_id
        self.name = 'root node %s' % root_id
        
    def do(self):
        node = self.get_node(self.root_id)
        if node:
            if self.fsck.forest.node_store.get_refcount(self.root_id) != 1:
                self.error('root refcount must be 1')
            if type(node) != larch.IndexNode:
                self.error('root must be an index node')
        else:
            self.error('missing root node %s' % self.root_id)


class CheckRecursively(WorkItem):

    def __init__(self, fsck, root_id, seen):
        self.fsck = fsck
        self.root_id = root_id
        self.name = 'tree %s' % root_id
        self.seen = seen
        
    def do(self):
        for node, minkey, maxkey in self.walk(self.root_id):
            if node.id not in self.seen:
                self.seen.add(node.id)
                keys = node.keys()
                if keys[0] < minkey:
                    self.error('node %s: first key is too small' % node.id)
                if keys[-1] > maxkey:
                    self.error('node %s: last key is too large' % node.id)

    def walk(self, root_id):

        def walker(node_id, minkey, maxkey, expected_type):
            expected_child = None
            node = self.get_node(node_id)
            if node:
                yield node, minkey, maxkey
                if type(node) == larch.IndexNode:
                    keys = node.keys()
                    for i, key in enumerate(keys):
                        child_id = node[key]
                        if i + 1 < len(keys):
                            next_key = keys[i+1]
                        else:
                            next_key = maxkey
                        if expected_child is None:
                            child = self.get_node(child_id)
                            if child:
                                expected_child = type(child)
                        for x in walker(child_id, key,  next_key, 
                                         expected_child):
                            yield x
            else:
                if expected_type == larch.IndexNode:
                    self.error('cannot find index node %s' % node_id)
                elif expected_type == larch.LeafNode:
                    self.error('cannot find leaf node %s' % node_id)
                else:
                    self.error('cannot find node of unknown type %s' % node_id)
        
        ns  = self.fsck.forest.node_store
        tree_minkey = chr(0) * ns.codec.key_bytes
        tree_maxkey = chr(255) * ns.codec.key_bytes
        for x in walker(root_id, tree_minkey, tree_maxkey, larch.IndexNode):
            yield x


class CheckExtraNodes(WorkItem):

    def __init__(self, fsck):
        self.fsck = fsck
        self.seen = set()
        self.name = 'extra nodes'

    def do(self):
        for node_id in self.fsck.forest.node_store.list_nodes():
            if node_id not in self.seen:
                self.error('node %d is not part of the tree' % node_id)


class Fsck(object):

    '''Verify internal consistency of a larch.Forest.'''
    
    def __init__(self, forest, report):
        self.forest = forest
        self.report = report
        self.work = []

    def find_work(self):
        for node_id in self.forest.node_store.list_nodes():
            self.work.append(CheckNode(self, node_id))
        for tree in self.forest.trees:
            self.work.append(CheckRoot(self, tree.root.id))
        extra = CheckExtraNodes(self)
        for tree in self.forest.trees:
            self.work.append(CheckRecursively(self, tree.root.id, extra.seen))
        self.work.append(extra)

