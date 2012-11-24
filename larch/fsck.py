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
import tracing
import ttystatus

import larch


class Error(larch.Error):

    def __init__(self, msg):
        self.msg = 'Assertion failed: %s' % msg


class WorkItem(object):

    '''A work item for fsck.
    
    Subclass can optionally set the ``name`` attribute; the class name
    is used by default.
    
    '''

    def __str__(self):
        if hasattr(self, 'name'):
            return self.name
        else:
            return self.__class__.__name__
    
    def do(self):
        pass

    def warning(self, msg):
        self.fsck.warning('warning: %s: %s' % (self.name, msg))

    def error(self, msg):
        self.fsck.error('ERROR: %s: %s' % (self.name, msg))

    def get_node(self, node_id):
        try:
            return self.fsck.forest.node_store.get_node(node_id)
        except larch.NodeMissing:
            self.error(
                'forest %s: node %s is missing' %
                    (self.fsck.forest_name, node_id))


class CheckNode(WorkItem):

    def __init__(self, fsck, node_id):
        self.fsck = fsck
        self.node_id = node_id
        self.name = 'node %s in %s' % (self.node_id, self.fsck.forest_name)

    def do(self):
        node = self.get_node(self.node_id)
        if type(node) == larch.IndexNode:
            for child_id in node.values():
                seen_already = child_id in self.fsck.refcounts
                self.fsck.count(child_id)
                if not seen_already:
                    yield CheckNode(self.fsck, child_id)

class CheckForest(WorkItem):

    def __init__(self, fsck):
        self.fsck = fsck
        self.name = 'forest %s' % self.fsck.forest_name

    def do(self):
        for tree in self.fsck.forest.trees:
            self.fsck.count(tree.root.id)
            yield CheckNode(self.fsck, tree.root.id)


class CheckRefcounts(WorkItem):

    def __init__(self, fsck):
        self.fsck = fsck
        self.name = 'refcounts in %s' % self.fsck.forest_name

    def do(self):
        for node_id in self.fsck.refcounts:
            refcount = self.fsck.forest.node_store.get_refcount(node_id)
            if refcount != self.fsck.refcounts[node_id]:
                self.error(
                    'forest %s: node %s: refcount is %s but should be %s' %
                        (self.fsck.forest_name,
                         node_id,
                         refcount,
                         self.fsck.refcounts[node_id]))
                if self.fsck.fix:
                    self.fsck.forest.node_store.set_refcount(node_id, refcount)


class CommitForest(WorkItem):

    def __init__(self, fsck):
        self.fsck = fsck
        self.name = 'committing fixes to %s' % self.fsck.forest_name

    def do(self):
        tracing.trace('committing changes to %s' % self.fsck.forest_name)
        self.fsck.forest.commit()


class Fsck(object):

    '''Verify internal consistency of a larch.Forest.'''
    
    def __init__(self, forest, warning, error, fix):
        self.forest = forest
        self.forest_name = getattr(
            forest.node_store, 'dirname', 'in-memory forest')
        self.warning = warning
        self.error = error
        self.fix = fix
        self.refcounts = {}

    def find_work(self):
        yield CheckForest(self)
        yield CheckRefcounts(self)
        if self.fix:
            yield CommitForest(self)

    def count(self, node_id):
        self.refcounts[node_id] = self.refcounts.get(node_id, 0) + 1

