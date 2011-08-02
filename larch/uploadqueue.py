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
import os
import StringIO
import struct
import tempfile

import larch


class UploadQueue(object):

    '''Queue of objects waiting to be uploaded to the store.
    
    We don't upload nodes directly, because it frequently happens
    that a node gets modified or deleted soon after it is created.
    It makes sense to wait a bit so we can avoid the costly upload
    operation.
    
    This class holds the nodes in a queue, and uploads them
    if they get pushed out of the queue.
    
    ``really_put`` is the function to call to really upload a node.
    ``max_length`` is the maximum number of nodes to keep in the queue.
    
    '''

    def __init__(self, really_put, max_length):
        self.really_put = really_put
        self._max_length = max_length
        self._create_lru()

    def _create_lru(self):
        self.lru = larch.LRUCache(self._max_length, 
                                  forget_hook=self._push_oldest)
        
    def put(self, node):
        '''Put a node into the queue.'''
        self.lru.add(node.id, node)

    def _push_oldest(self, node_id, node):
        self.really_put(node)

    def push(self):
        '''Upload all nodes in the queue.'''
        while len(self.lru) > 0:
            node_id, node = self.lru.remove_oldest()
            self.really_put(node)
        self.lru.log_stats()
        self._create_lru()
    
    def remove(self, node_id):
        '''Remove a node from the queue given its id.'''
        return self.lru.remove(node_id)
        
    def list_ids(self):
        '''List identifiers of all nodes in the queue.'''
        return self.lru.keys()
        
    def get(self, node_id):
        '''Get a node node given its id.'''
        return self.lru.get(node_id)

