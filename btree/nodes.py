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


class Node(dict):

    '''Abstract base class for index and leaf nodes.
    
    A node may be initialized with a list of (key, value) pairs. For
    leaf nodes, the values are the actual values. For index nodes, they
    are references to other nodes.
    
    '''

    def __init__(self, node_id, pairs=None):
        dict.__init__(self, pairs or [])
        self.id = node_id

    def keys(self):
        '''Return keys in the node, sorted.'''
        return sorted(dict.keys(self))

    def first_key(self):
        '''Return smallest key in the node.'''
        return self.keys()[0]

    def pairs(self, exclude=None):
        '''Return (key, value) pairs in the node.
        
        ``exclude`` can be set to a list of keys that should be excluded
        from the list.
        
        '''

        if exclude is None:
            exclude = []
        return sorted((key, self[key]) for key in self if key not in exclude)


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
        for k in reversed(self.keys()):
            if key >= k:
                return k
        return None

