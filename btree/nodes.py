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


import btree


class Node(object):

    '''Abstract base class for index and leaf nodes.
    
    A node may be initialized with a list of (key, value) pairs. For
    leaf nodes, the values are the actual values. For index nodes, they
    are references to other nodes.
    
    '''

    def __init__(self, node_id, pairs=None):
        self._pairs = (pairs or [])[:]
        self._dict = dict(pairs)
        self.id = node_id
        self.size = None

    def __getitem__(self, key):
        return self._dict[key]

    def __contains__(self, key):
        return key in self._dict

    def __eq__(self, other):
        return self._pairs == other._pairs

    def __iter__(self):
        for key, value in self._pairs:
            yield key

    def __len__(self):
        return len(self._pairs)

    def keys(self):
        '''Return keys in the node, sorted.'''
        return [k for k, v in self._pairs]

    def values(self):
        '''Return value sin the key, in same order as keys.'''
        return [v for k, v in self._pairs]

    def first_key(self):
        '''Return smallest key in the node.'''
        return self._pairs[0][0]

    def pairs(self, exclude=None):
        '''Return (key, value) pairs in the node.
        
        ``exclude`` can be set to a list of keys that should be excluded
        from the list.
        
        '''

        if exclude is None:
            return self._pairs
        else:
            return [(k, v) for k, v in self._pairs if k not in exclude]

    def add(self, key, value):
        '''Insert a key/value pair into the right place in a node.'''
        
        getkey = lambda pair: pair[0]
        i, j = btree.bsearch(self._pairs, key, getkey=getkey)
        
        pair = (key, value)
        if i is None:
            self._pairs.insert(0, pair)
        elif i == j:
            self._pairs[i] = pair
        else:
            self._pairs.insert(i+1, pair)

    def remove(self, key):
        '''Remove a key from the node.
        
        Raise KeyError if key does not exist in node.
        
        '''
        
        getkey = lambda pair: pair[0]
        i, j = btree.bsearch(self._pairs, key, getkey=getkey)
        if i == j and i is not None:
            del self._pairs[i]
        else:
            raise KeyError(key)

class LeafNode(Node):

    '''Leaf node in the tree.
    
    A leaf node contains key/value pairs, and has no children.
    
    '''

    pass


class IndexNode(Node):

    '''Index node in the tree.
    
    An index node contains pairs of keys and references to other nodes.
    The other nodes may be either index nodes or leaf nodes.
    
    '''

    def __init__(self, node_id, pairs):
        for key, child in pairs:
            assert type(key) == str
            assert type(child) == int
        Node.__init__(self, node_id, pairs)

    def find_key_for_child_containing(self, key):
        '''Return key for the child that contains ``key``.'''
        getkey = lambda pair: pair[0]
        lo, hi = btree.bsearch(self._pairs, key, getkey=getkey)
        if lo is None:
            return None
        else:
            return getkey(self._pairs[lo])
