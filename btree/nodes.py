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


import bisect

import btree


class Node(object):

    '''Abstract base class for index and leaf nodes.
    
    A node may be initialized with a list of (key, value) pairs. For
    leaf nodes, the values are the actual values. For index nodes, they
    are references to other nodes.
    
    '''

    def __init__(self, node_id, keys, values):
        self._keys = list(keys)
        self._values = list(values)
        self._dict = dict()
        for i in range(len(keys)):
            self._dict[keys[i]] = values[i]
        self.id = node_id
        self.size = None

    def __getitem__(self, key):
        return self._dict[key]

    def __contains__(self, key):
        return key in self._dict

    def __eq__(self, other):
        return self._keys == other._keys and self._values == other._values

    def __iter__(self):
        for key in self._keys:
            yield key

    def __len__(self):
        return len(self._keys)

    def keys(self):
        '''Return keys in the node, sorted.'''
        return self._keys

    def values(self):
        '''Return value sin the key, in same order as keys.'''
        return self._values

    def first_key(self):
        '''Return smallest key in the node.'''
        return self._keys[0]

    def find_potential_range(self, minkey, maxkey):
        '''Find pairs whose key is in desired range.

        minkey and maxkey are inclusive.

        We take into account that for index nodes, a child's key
        really represents a range of keys, from the key up to (but
        not including) the next child's key. The last child's key
        represents a range up to infinity.

        Thus we return the first child, if its key lies between
        minkey and maxkey, and the last child, if its key is at most
        maxkey.

        '''
        
        def helper(key, default):
            x = bisect.bisect_left(self._keys, key)
            if x < len(self._keys):
                if self._keys[x] > key:
                    if x == 0:
                        x = default
                    else:
                        x -= 1
            else:
                if x == 0:
                    x = None
                else:
                    x -= 1
            return x

        i = helper(minkey, 0)
        j = helper(maxkey, None)
        if j is None:
            i = None

        return i, j

    def add(self, key, value):
        '''Insert a key/value pair into the right place in a node.'''
        
        i = bisect.bisect_left(self._keys, key)
        if i < len(self._keys) and self._keys[i] == key:
            self._keys[i] = key
            self._values[i] = value
        else:
            self._keys.insert(i, key)
            self._values.insert(i, value)

        self._dict[key] = value
        self.size = None

    def remove(self, key):
        '''Remove a key from the node.
        
        Raise KeyError if key does not exist in node.
        
        '''
        
        i = bisect.bisect_left(self._keys, key)
        if i >= len(self._keys) or self._keys[i] != key:
            raise KeyError(key)
        del self._keys[i]
        del self._values[i]
        del self._dict[key]
        self.size = None
        
    def remove_index_range(self, lo, hi):
        '''Remove keys given a range of indexes into pairs.
        
        lo and hi are inclusive.
        
        '''
        
        del self._keys[lo:hi+1]
        del self._values[lo:hi+1]
        self.size = None


class LeafNode(Node):

    '''Leaf node in the tree.
    
    A leaf node contains key/value pairs, and has no children.
    
    '''

    def find_keys_in_range(self, minkey, maxkey):
        '''Find pairs whose key is in desired range.
        
        minkey and maxkey are inclusive.
        
        '''
        
        i = bisect.bisect_left(self._keys, minkey)
        j = bisect.bisect_left(self._keys, maxkey)
        if j < len(self._keys) and self._keys[j] == maxkey:
            j += 1
        return self._keys[i:j]


class IndexNode(Node):

    '''Index node in the tree.
    
    An index node contains pairs of keys and references to other nodes.
    The other nodes may be either index nodes or leaf nodes.
    
    '''

    def find_key_for_child_containing(self, key):
        '''Return key for the child that contains ``key``.'''

        i = bisect.bisect_left(self._keys, key)
        if i < len(self._keys):
            if self._keys[i] == key:
                return key
            elif i == 0:
                return None
            else:
                return self._keys[i-1]
        elif i == 0:
            return None
        else:
            return self._keys[i-1]

    def find_children_in_range(self, minkey, maxkey):
        '''Find all children whose key is in the range.
        
        minkey and maxkey are inclusive. Note that a child might
        be returned even if not all of its keys are in the range,
        just some of them. Also, we consider potential keys here,
        not actual keys. We have no way to retrieve the children
        to check which keys they actually have, so instead we
        return which keys might have the desired keys, and the
        caller can go look at those.
        
        '''
        
        i, j = self.find_potential_range(minkey, maxkey)
        if i is not None and j is not None:
            return self._values[i:j+1]
        else:
            return []

