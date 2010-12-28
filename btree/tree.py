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

import btree


'''A simple B-tree implementation.'''


class KeySizeMismatch(Exception):

    def __init__(self, key, wanted_size):
        self.key = key
        self.wanted_size = wanted_size
        
    def __str__(self):
        return 'Key %s is of wrong length (%d, should be %d)' % \
                (repr(self.key), len(self.key), self.wanted_size)
       

class BTree(object):

    '''B-tree.
    
    The nodes are stored in an external node store; see the NodeStore
    class. Key sizes are fixed, and given in bytes.
    
    '''

    def __init__(self, forest, node_store, root_id):
        self.forest = forest
        self.node_store = node_store

        self.max_index_length = self.node_store.max_index_pairs()
        self.min_index_length = self.max_index_length / 2

        if root_id is None:
            self.root = None
        else:
            self.root = self.get_node(root_id)

    def check_key_size(self, key):
        if len(key) != self.node_store.codec.key_bytes:
            raise KeySizeMismatch(key, self.node_store.codec.key_bytes)

    def new_id(self):
        '''Generate a new node identifier.'''
        return self.forest.new_id()
    
    def node_can_be_modified_in_place(self, node):
        '''Can a node be modified in place, in memory?
        
        This is true if there is only parent (refcount is 1).
        
        '''
        
        return self.node_store.get_refcount(node.id) == 1
    
    def new_leaf(self, pairs):
        '''Create a new leaf node and keep track of it.'''
        leaf = btree.LeafNode(self.new_id(), pairs)
        self.node_store.put_node(leaf)
        return leaf
        
    def new_index(self, pairs):
        '''Create a new index node and keep track of it.'''
        index = btree.IndexNode(self.new_id(), pairs)
        self.node_store.put_node(index)
        for key, child_id in pairs:
            self.increment(child_id)
        return index
        
    def new_root(self, pairs):
        '''Create a new root node and keep track of it.'''
        self.root = self.new_index(pairs)
        self.node_store.set_refcount(self.root.id, 1)

    def get_node(self, node_id):
        '''Return node corresponding to a node id.'''
        return self.node_store.get_node(node_id)

    def put_node(self, node):
        '''Put node into node store.'''
        return self.node_store.put_node(node)

    def _leaf_size(self, node):
        if node.size is None:
            node.size = self.node_store.codec.leaf_size(node.pairs())
        return node.size

    def lookup(self, key):
        '''Return value corresponding to ``key``.
        
        If the key is not in the tree, raise ``KeyError``.
        
        '''

        self.check_key_size(key)

        node = self.root
        while node and isinstance(node, btree.IndexNode):
            k = node.find_key_for_child_containing(key)
            if k is None:
                raise KeyError(key)
            node_id = node[k]
            node = self.get_node(node_id)
            
        if node and isinstance(node, btree.LeafNode):
            return node[key]

        raise KeyError(key)

    def lookup_range(self, minkey, maxkey):
        '''Return list of (key, value) pairs for all keys in a range.

        minkey and maxkey are included in range.

        '''

        self.check_key_size(minkey)
        self.check_key_size(maxkey)
        if self.root is not None:
            for pair in self._lookup_range(self.root.id, minkey, maxkey):
                yield pair

    def _lookup_range(self, node_id, minkey, maxkey):
        node = self.get_node(node_id)
        if isinstance(node, btree.LeafNode):
            for pair in node.find_pairs(minkey, maxkey):
                yield pair
        else:
            assert isinstance(node, btree.IndexNode)
            result = []
            for child_id in node.find_children_in_range(minkey, maxkey):
                for pair in self._lookup_range(child_id, minkey, maxkey):
                    yield pair

    def range_is_empty(self, minkey, maxkey):
        '''Is a range empty in the tree?
        
        This is faster than doing a range lookup for the same range,
        and checking if there are any keys returned.
        
        '''
        
        self.check_key_size(minkey)
        self.check_key_size(maxkey)
        if self.root is None:
            return True
        return self._range_is_empty(self.root.id, minkey, maxkey)

    def _range_is_empty(self, node_id, minkey, maxkey):
        node = self.get_node(node_id)
        if isinstance(node, btree.LeafNode):
            return node.find_pairs(minkey, maxkey) == []
        else:
            assert isinstance(node, btree.IndexNode)
            for child_id in node.find_children_in_range(minkey, maxkey):
                if not self._range_is_empty(child_id, minkey, maxkey):
                    return False
            return True

    def _shadow(self, node):
        '''Shadow a node: make it possible to modify it in-place.'''
        
        if self.node_can_be_modified_in_place(node):
            return node
        else:
            if isinstance(node, btree.IndexNode):
                new = self.new_index(node.pairs())
            else:
                new = self.new_leaf(node.pairs())
                new.size = node.size
            self.put_node(new)
            return new
        
    def insert(self, key, value):
        '''Insert a new key/value pair into the tree.
        
        If the key already existed in the tree, the old value is silently
        forgotten.
        
        '''

        self.check_key_size(key)

        # Is the tree empty? This needs special casing to keep
        # _insert_into_index simpler.
        if self.root is None or len(self.root) == 0:
            leaf = btree.LeafNode(self.new_id(), [(key, value)])
            self.put_node(leaf)
            if self.root is None:
                self.new_root([(key, leaf.id)])
            else:
                self.root.add(key, leaf.id)
                self.increment(leaf.id)
            return

        kids = self._insert_into_index(self.root, key, value)
        # kids is either [self.root] or it is two children, in which case
        # a new root needs to be created.
        if len(kids) > 1:
            pairs = [(kid.first_key(), kid.id) for kid in kids]
            old_root_id = self.root.id
            assert old_root_id is not None
            self.new_root(pairs)
            self.decrement(old_root_id)

    def _insert_into_index(self, old_index, key, value):
        '''Insert key, value into an index node.
        
        Return list of replacement nodes. Might be just the same node,
        or a single new node, or two nodes, one of which might be the
        same node. Note that this method never makes the tree higher,
        that is the job of the caller. If two nodes are returned,
        they are siblings at the same height as the original node.
        
        '''

        new_index = self._shadow(old_index)

        child_key = new_index.find_key_for_child_containing(key)
        if child_key is None:
            child_key = new_index.first_key()

        child = self.get_node(new_index[child_key])
        if isinstance(child, btree.IndexNode):
            new_kids = self._insert_into_index(child, key, value)
        else:
            new_kids = self._insert_into_leaf(child, key, value)

        new_index.remove(child_key)
        for kid in new_kids:
            new_index.add(kid.first_key(), kid.id)
            self.increment(kid.id)
        self.decrement(child.id)

        if len(new_index) > self.max_index_length:
            n = len(new_index) / 2
            pairs = new_index.pairs()[n:]
            new = btree.IndexNode(self.new_id(), pairs)
            for k, v in pairs:
                new_index.remove(k)
            self.put_node(new_index)
            self.put_node(new)
            return [new_index, new]
        else:
            self.put_node(new_index)
            return [new_index]

    def _insert_into_leaf(self, leaf, key, value):
        '''Insert a key/value pair into a leaf node.
        
        Return value is like for _insert_into_index.
        
        '''
        
        clone = self._shadow(leaf)
        clone.add(key, value)
        
        pairs = []
        while self._leaf_size(clone) > self.node_store.node_size:
            key, value = clone.pairs()[0]
            pairs.append((key, value))
            clone.remove(key)
            
        if pairs:
            new = self.new_leaf(pairs)
            leaves = [new, clone]
        else:
            leaves = [clone]
        
        for x in leaves:
            self.put_node(x)
        return leaves

    def remove(self, key):
        '''Remove ``key`` and its associated value from tree.
        
        If key is not in the tree, ``KeyValue`` is raised.
        
        '''
    
        self.check_key_size(key)

        if self.root is None:
            raise KeyError(key)

        self._remove_from_index(self.root, key)
        self._reduce_height()

    def _remove_from_index(self, old_index, key):
        child_key = old_index.find_key_for_child_containing(key)
        new_index = self._shadow(old_index)
        child = self.get_node(new_index[child_key])
        
        if isinstance(child, btree.IndexNode):
            new_kid = self._remove_from_index(child, key)
            new_index.remove(child_key)
            if len(new_kid) > 0:
                self._add_or_merge_index(new_index, new_kid)
            self.decrement(child.id)
        else:
            assert isinstance(child, btree.LeafNode)
            leaf = self._shadow(child)
            leaf.remove(key)
            new_index.remove(child_key)
            if len(leaf) > 0:
                self._add_or_merge_leaf(new_index, leaf)
                self.decrement(child.id)
            else:
                self.decrement(leaf.id)
                if child.id != leaf.id: # pragma: no cover
                    self.decrement(child.id)

        self.put_node(new_index)
        return new_index

    def _add_or_merge_index(self, parent, index):
        self._add_or_merge(parent, index, self._merge_index)

    def _add_or_merge_leaf(self, parent, leaf):
        self._add_or_merge(parent, leaf, self._merge_leaf)

    def _add_or_merge(self, parent, node, merge):
        pairs = parent.pairs()
        getkey = lambda pair: pair[0]
        i, j = btree.bsearch(pairs, node.first_key(), getkey=getkey)
        if i is None or not merge(parent, node, i):
            if j is not None:
                merge(parent, node, j)

        self.put_node(node)
        parent.add(node.first_key(), node.id)
        self.increment(node.id)

    def _merge_index(self, parent, node, sibling_index):

        def merge_indexes_p(a, b):
            return len(a) + len(b) <= self.max_index_length

        def add_to_index(n, k, v):
            n.add(k, v)
            self.increment(v)

        return self._merge_nodes(parent, node, sibling_index,
                                 merge_indexes_p, add_to_index)

    def _merge_leaf(self, parent, node, sibling_index):

        def merge_leaves_p(a, b):
            a_size = self._leaf_size(a)
            b_size = self._leaf_size(b)
            return a_size + b_size <= self.node_store.node_size

        def add_to_leaf(n, k, v):
            n.add(k, v)

        return self._merge_nodes(parent, node, sibling_index,
                                 merge_leaves_p, add_to_leaf)

    def _merge_nodes(self, parent, node, sibling_index, merge_p, add):
        pairs = parent.pairs()
        sibling_key, sibling_id = pairs[sibling_index]
        sibling = self.get_node(sibling_id)
        if merge_p(node, sibling):
            for k, v in sibling.pairs():
                add(node, k, v)
            parent.remove(sibling_key)
            self.decrement(sibling.id)
            return True
        else:
            return False

    def remove_range(self, minkey, maxkey):
        '''Remove all keys in the given range.

        Range is inclusive.

        '''

        self.check_key_size(minkey)
        self.check_key_size(maxkey)
        self._remove_range_from_index(self.root, minkey, maxkey)
        self._reduce_height()

    def _remove_range_from_index(self, index, minkey, maxkey):
        new = self._shadow(index)

        lo, hi = new.find_potential_range(minkey, maxkey)
        if (lo, hi) == (None, None):
            return new

        for key, child_id in new.pairs()[lo:hi+1]:
            child = self.get_node(child_id)
            if isinstance(child, btree.IndexNode):
                new_kid = self._remove_range_from_index(child, minkey, maxkey)
            else:
                new_kid = self._remove_range_from_leaf(child, minkey, maxkey)
            if len(new_kid) == 0:
                new.remove(key)
                for x in set([new_kid.id, child.id]):
                    self.decrement(x)
            else:
                new.remove(key)
                new.add(new_kid.first_key(), new_kid.id)
                self.increment(new_kid.id)
                self.decrement(child.id)

        return new

    def _remove_range_from_leaf(self, leaf, minkey, maxkey):
        new = self._shadow(leaf)
        for key, value in new.find_pairs(minkey, maxkey):
            new.remove(key)
        return new

    def _reduce_height(self):
        # After removing things, the top of the tree might consist of a
        # list of index nodes with only a single child, which is also
        # an index node. These can and should be removed, for efficiency.
        # Further, since we've modified all of these nodes, they can all
        # be modified in place.
        while len(self.root) == 1:
            key, child_id = self.root.pairs()[0]
            assert self.node_can_be_modified_in_place(self.root)
            assert self.node_store.get_refcount(self.root.id) == 1
            
            if self.node_store.get_refcount(child_id) != 1:
                break

            child = self.get_node(child_id)
            if isinstance(child, btree.LeafNode):
                break

            # We can just make the child be the new root node.
            self.root.remove(key)
            self.put_node(self.root) # So decrement gets modified root.
            self.decrement(self.root.id)
            self.root = child

    def increment(self, node_id):
        '''Non-recursively increment refcount for a node.'''
        refcount = self.node_store.get_refcount(node_id)
        self.node_store.set_refcount(node_id, refcount + 1)

    def decrement(self, node_id):
        '''Recursively, lazily decrement refcounts for a node and children.'''
        refcount = self.node_store.get_refcount(node_id)
        if refcount > 1:
            self.node_store.set_refcount(node_id, refcount - 1)
        else:
            node = self.node_store.get_node(node_id)
            if isinstance(node, btree.IndexNode):
                for key, child_id in node.pairs():
                    self.decrement(child_id)
            self.node_store.remove_node(node_id)
            self.node_store.set_refcount(node_id, 0)

    def dump(self, f, msg=None, keymangler=str, valuemangler=str): # pragma: no cover
        '''Dump tree structure to open file f.'''
        
        def dumper(node, indent):
            refs = self.node_store.get_refcount(node.id)
            if isinstance(node, btree.IndexNode):
                f.write('%*sindex (id=%d, refs=%d)\n' % (indent*2, '', node.id, refs))
                for key, child_id in node.pairs():
                    child = self.get_node(child_id)
                    dumper(child, indent + 1)
            else:
                assert isinstance(node, btree.LeafNode)
                f.write('%*sleaf (id=%d, refs=%d, len=%d):' % 
                        (indent*2, '', node.id, refs, len(node)))
                for key, value in node.pairs():
                    f.write(' %s=%s' % (keymangler(key), valuemangler(value)))
                f.write('\n')
        
        if msg is not None:
            f.write('%s\n' % msg)
        f.write('Dumping tree %s\n' % self)
        dumper(self.root, 1)
