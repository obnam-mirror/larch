# Copyright 2010  Lars Wirzenius, Richard Braakman
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


import heapq
import logging


class LRUCache(object):

    '''A least-recently-used cache.

    This class caches objects, based on keys. The cache has a fixed size,
    in number of objects. When a new object is added to the cache, the
    least recently used old object is dropped. Each object is associated
    with a key, and use is defined as retrieval of the object using the key.
    
    Two hooks are provided for: for removing an object by user request, 
    and when it is automatically removed due to cache overflow. Either
    hook is called with the key and object as arguments.

    '''

    def __init__(self, max_size, remove_hook=None, forget_hook=None):
        self.max_size = max_size
        # Together, obj_before and obj_after form a random access
        # double-linked sequence. None used as the sentinel on both ends.
        self.obj_before = dict()
        self.obj_after = dict()
        self.obj_before[None] = None
        self.obj_after[None] = None
        self.ids = dict()  # maps key to object
        self.objs = dict() # maps object to key
        self.remove_hook = remove_hook
        self.forget_hook = forget_hook
        self.hits = 0
        self.misses = 0

    def __del__(self):
        logging.info('LRUCache %s: hits=%s misses=%s' % 
                     (self, self.hits, self.misses))

    def __len__(self):
        return len(self.ids)

    def keys(self):
        '''List keys for objects in cache.'''
        return self.ids.keys()

    def add(self, key, obj):
        '''Add new item to cache.'''
        if key in self.ids:
            self.remove(key)
        before = self.obj_before[None]
        self.obj_before[None] = obj
        self.obj_before[obj] = before
        self.obj_after[before] = obj
        self.obj_after[obj] = None
        self.ids[key] = obj
        self.objs[obj] = key
        while len(self.ids) > self.max_size:
            self._forget_oldest()

    def _forget_oldest(self):
        obj = self.obj_after[None]
        key = self.objs[obj]
        self._remove(key)
        if self.forget_hook:
            self.forget_hook(key, obj)
        
    def _remove(self, key):
        obj = self.ids[key]
        before = self.obj_before[obj]
        after = self.obj_after[obj]
        self.obj_before[after] = before
        self.obj_after[before] = after
        del self.obj_before[obj]
        del self.obj_after[obj]
        del self.ids[key]
        del self.objs[obj]
        
    def get(self, key):
        '''Retrieve item from cache.

        Return object associated with key, or None.

        '''
        
        if key in self.ids:
            self.hits += 1
            obj = self.ids[key]
            self.remove(key)
            self.add(key, obj)
            return obj
        else:
            self.misses += 1
            return None
        
    def remove(self, key):
        '''Remove an item from the cache.
        
        Return True if item was in cache, False otherwise.
        
        '''

        if key in self.ids:
            obj = self.ids[key]
            self._remove(key)
            if self.remove_hook:
                self.remove_hook(key, obj)
            return True
        else:
            return False

    def remove_oldest(self):
        '''Remove oldest object.
        
        Return key and object.
        
        '''

        obj = self.obj_after[None]
        key = self.objs[obj]
        self.remove(key)
        return key, obj

