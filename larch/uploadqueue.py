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
import lru
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
        self.lru = lru.LRUCache(max_length, forget_hook=self._push_oldest)
        
    def put(self, node):
        self.lru.add(node.id, node)

    def _push_oldest(self, node_id, node):
        self.really_put(node)

    def push(self):
        while len(self.lru) > 0:
            node_id, node = self.lru.remove_oldest()
            self.really_put(node)
    
    def remove(self, node_id):
        return self.lru.remove(node_id)
        
    def list_ids(self):
        return self.lru.keys()
        
    def get(self, node_id):
        return self.lru.get(node_id)

