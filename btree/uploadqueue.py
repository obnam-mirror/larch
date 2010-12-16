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


import ConfigParser
import logging
import os
import StringIO
import struct
import tempfile

import btree


class UploadQueue(object):

    '''Queue of objects waiting to be uploaded to the store.
    
    We don't upload nodes directly, because it frequently happens
    that a node gets modified or deleted soon after it is created,
    it makes sense to wait a bit so we can avoid the costly upload
    operation.
    
    This class holds the nodes in a queue, and uploads them
    if they get pushed out of the queue.
    
    '''

    def __init__(self, really_put, max_length):
        self.really_put = really_put
        self.max = max_length
        # Together, node_before and node_after form a random access
        # double-linked sequence. None used as the sentinel on both ends.
        self.node_before = dict()
        self.node_after = dict()
        self.node_before[None] = None
        self.node_after[None] = None
        self.ids = dict()  # maps node.id to node
        
    def put(self, node):
        if node.id in self.ids:
            self.remove(node.id)
        before = self.node_before[None]
        self.node_before[None] = node
        self.node_before[node] = before
        self.node_after[before] = node
        self.node_after[node] = None
        self.ids[node.id] = node
        while len(self.ids) > self.max:
            self._push_oldest()

    def _push_oldest(self):
        node = self.node_after[None]
        assert node is not None, \
            'node is None\nids: %s\nafter: %s\nbefore: %s' % \
            (repr(self.ids), self.node_after, self.node_before)
        self.remove(node.id)
        self.really_put(node)

    def push(self):
        while self.ids:
            self._push_oldest()
    
    def remove(self, node_id):
        if node_id in self.ids:
            node = self.ids[node_id]
            assert node.id == node_id
            before = self.node_before[node]
            after = self.node_after[node]
            self.node_before[after] = before
            self.node_after[before] = after
            del self.node_before[node]
            del self.node_after[node]
            del self.ids[node_id]
            return True
        else:
            return False
        
    def list_ids(self):
        return self.ids.keys()
        
    def get(self, node_id):
        return self.ids.get(node_id)

