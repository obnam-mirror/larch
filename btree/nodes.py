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
            pairs = self.pairs()
            getkey = lambda pair: pair[0]
            x = bisect.bisect_left(pairs, (key, None))
            if x < len(pairs):
                if getkey(pairs[x]) > key:
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
        
        i = bisect.bisect_left(self._pairs, (key, None))
        if i < len(self._pairs) and self._pairs[i][0] == key:
            self._pairs[i] = (key, value)
        else:
            self._pairs.insert(i, (key, value))

        self._dict[key] = value
        self.size = None

    def remove(self, key):
        '''Remove a key from the node.
        
        Raise KeyError if key does not exist in node.
        
        '''
        
        getkey = lambda pair: pair[0]
        i, j = btree.bsearch(self._pairs, key, getkey=getkey)
        if i == j and i is not None:
            del self._pairs[i]
            del self._dict[key]
        else:
            raise KeyError(key)
        self.size = None
        
    def remove_index_range(self, lo, hi):
        '''Remove keys given a range of indexes into pairs.
        
        lo and hi are inclusive.
        
        '''
        
        del self._pairs[lo:hi+1]
        self.size = None


class LeafNode(Node):

    '''Leaf node in the tree.
    
    A leaf node contains key/value pairs, and has no children.
    
    '''

    def find_pairs(self, minkey, maxkey):
        '''Find pairs whose key is in desired range.
        
        minkey and maxkey are inclusive.
        
        '''
        
        getkey = lambda pair: pair[0]
        min_lo, min_hi = btree.bsearch(self._pairs, minkey, getkey=getkey)
        max_lo, max_hi = btree.bsearch(self._pairs, maxkey, getkey=getkey)

        if min_hi is None or max_lo is None:
            return []
        i = min_hi
        j = max_lo

        return self._pairs[i:j+1]


class IndexNode(Node):

    '''Index node in the tree.
    
    An index node contains pairs of keys and references to other nodes.
    The other nodes may be either index nodes or leaf nodes.
    
    '''

    def find_key_for_child_containing(self, key):
        '''Return key for the child that contains ``key``.'''
        getkey = lambda pair: pair[0]
        lo, hi = btree.bsearch(self._pairs, key, getkey=getkey)
        if lo is None:
            return None
        else:
            return getkey(self._pairs[lo])

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
        
        getkey = lambda pair: pair[0]
        getchild = lambda pair: pair[1]
        
        a, b = btree.bsearch(self._pairs, minkey, getkey=getkey)
        i, j = btree.bsearch(self._pairs, maxkey, getkey=getkey)
        
        if a is not None:
            lo = a
        elif b is not None:
            lo = b
        else:
            return []

        if i is None:
            return []

        return [getchild(pair) for pair in self._pairs[lo:i+1]]

