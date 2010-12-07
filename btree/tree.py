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


'''A simple B-tree implementation.

Some notes:

* No nodes are modified, everything is done copy-on-write. This is because
  eventually this code will be used to handle on-disk data structures where
  copy-on-write is essential.
* The fullness of leaf and index nodes is determined by number of keys.
  This is appropriate for now, but eventually we will want to inspect the
  size in bytes of the nodes instead. This is also for on-disk data
  structures, where fixed-sized disk sectors or such are used to store
  the nodes.

'''


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
    
    The tree is balanced.
    
    Three basic operations are available to the tree: lookup, insert, and
    remove.
    
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
            self.increment(child_id) # pragma: no cover
        return index
        
    def set_root(self, node):
        '''Use a (newly created) node as the new root.'''
        self.root = node
        self.node_store.set_refcount(node.id, 1)

    def new_root(self, pairs):
        '''Create a new root node and keep track of it.'''
        self.set_root(self.new_index(pairs))

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
        if self.root is None:
            raise KeyError(key)
        return self._lookup(self.root.id, key)

    def _lookup(self, node_id, key):
        node = self.get_node(node_id)
        if isinstance(node, btree.LeafNode):
            return node[key]
        else:
            k = node.find_key_for_child_containing(key)
            if k is None:
                raise KeyError(key)
            else:
                return self._lookup(node[k], key)

    def lookup_range(self, minkey, maxkey):
        '''Return list of (key, value) pairs for all keys in a range.

        minkey and maxkey are included in range.

        '''

        if self.root is None:
            return []
        return self._lookup_range(self.root.id, minkey, maxkey)

    def _lookup_range(self, node_id, minkey, maxkey):
        node = self.get_node(node_id)
        if isinstance(node, btree.LeafNode):
            return self._lookup_range_in_leaf(node, minkey, maxkey)
        else:
            assert isinstance(node, btree.IndexNode)
            result = []
            for child_id in node.find_children_in_range(minkey, maxkey):
                result += self._lookup_range(child_id, minkey, maxkey)
            return result

    def _lookup_range_in_leaf(self, leaf, minkey, maxkey):
        pairs = leaf.pairs()
        getkey = lambda pair: pair[0]
        min_lo, min_hi = btree.bsearch(pairs, minkey, getkey=getkey)
        max_lo, max_hi = btree.bsearch(pairs, maxkey, getkey=getkey)

        if min_hi is None:
            return []
        i = min_hi
        j = max_lo

        return pairs[i:j+1]

    def _new_root(self, pairs):
        '''Create a new root node for this tree.'''
        root = btree.IndexNode(self.new_id(), pairs)
        self.put_node(root)
        self.node_store.set_refcount(root.id, 1)
        self.root = root

    def _clone_node(self, node):
        '''Make a new, identical copy of a node.
        
        Same contents, new id.
        
        '''

        if isinstance(node, btree.IndexNode):
            new = btree.IndexNode(self.new_id(), node.pairs())
        else:
            new = btree.LeafNode(self.new_id(), node.pairs())
            new.size = node.size
        self.put_node(new)
        return new

    def _shadow(self, node):
        '''Shadow a node: make it possible to modify it in-place.'''
        
        if self.node_can_be_modified_in_place(node):
            return node
        else:
            return self._clone_node(node)
        
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
                self._new_root([(key, leaf.id)])
            else:
                self.root.add(key, leaf.id)
            self.increment(leaf.id)
            return

        kids = self._insert_into_index(self.root, key, value)
        if len(kids) > 1:
            pairs = [(kid.first_key(), kid.id) for kid in kids]
            old_root_id = self.root.id
            assert old_root_id is not None
            self._new_root(pairs)
            for kid in kids:
                self.increment(kid.id)
            self.decrement(old_root_id)

    def _insert_into_index(self, old_index, key, value):
        '''Insert key, value into an index node.
        
        Return list of replacement nodes. Might be just the same node,
        or a single new node, or two nodes, one of which might be the
        same node.
        
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
        if self._leaf_size(clone) > self.node_store.node_size:
            n = len(clone) / 2
            pairs = clone.pairs()[n:]
            new = btree.LeafNode(self.new_id(), pairs)
            for k, v in pairs:
                clone.remove(k)
            leaves = [clone, new]
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

        assert self.node_store.get_refcount(self.root.id) == 1
        self._remove_from_index(self.root, key)
        self._remove_single_index_children()

    def _remove_single_index_children(self):
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
                break # pragma: no cover

            child = self.get_node(child_id)
            if isinstance(child, btree.LeafNode):
                break

            # We can just make the child be the new root node.
            self.root.remove(key)
            self.put_node(self.root) # So decrement gets modified root.
            self.decrement(self.root.id)
            self.root = child

    def _remove_from_index(self, index, key):
        child_key = index.find_key_for_child_containing(key)
        if child_key is None: # pragma: no cover
            raise KeyError(key)

        index = self._shadow(index)
        child = self.get_node(index[child_key])
        
        if isinstance(child, btree.IndexNode):
            new_kid = self._remove_from_index(child, key)
            index.remove(child_key)
            if len(new_kid) > 0:
                self._add_or_merge_index(index, new_kid)
            self.decrement(child.id)
        else:
            assert isinstance(child, btree.LeafNode)
            leaf = self._shadow(child)
            leaf.remove(key)
            index.remove(child_key)
            if len(leaf) > 0:
                self._add_or_merge_leaf(index, leaf)
                self.decrement(child.id)
            else:
                self.decrement(leaf.id)
                if child.id != leaf.id: # pragma: no cover
                    self.decrement(child.id)

        self.put_node(index)
        return index

    def _add_or_merge_index(self, parent, index):
        pairs = parent.pairs()
        getkey = lambda pair: pair[0]
        i, j = btree.bsearch(pairs, index.first_key(), getkey=getkey)
        if i is None or not self._merge_index(parent, index, i):
            if j is not None:
                self._merge_index(parent, index, j)

        self.put_node(index)
        parent.add(index.first_key(), index.id)
        self.increment(index.id)

    def _merge_index(self, parent, index, sibling_index):
        pairs = parent.pairs()
        sibling_key, sibling_id = pairs[sibling_index]
        sibling = self.get_node(sibling_id)
        if len(sibling) + len(index) <= self.max_index_length:
            for k, v in sibling.pairs():
                index.add(k, v)
                self.increment(v)
            parent.remove(sibling_key)
            self.decrement(sibling.id)
            return True
        else:
            return False
        
    def _add_or_merge_leaf(self, parent, leaf):
        pairs = parent.pairs()
        getkey = lambda pair: pair[0]
        i, j = btree.bsearch(pairs, leaf.first_key(), getkey=getkey)
        if i is None or not self._merge_leaf(parent, leaf, i):
            if j is not None:
                self._merge_leaf(parent, leaf, j)

        self.put_node(leaf)
        parent.add(leaf.first_key(), leaf.id)
        self.increment(leaf.id)

    def _merge_leaf(self, parent, leaf, sibling_index):
        pairs = parent.pairs()
        sibling_id = pairs[sibling_index][1]
        sibling = self.get_node(sibling_id)
        sibling_size = self._leaf_size(sibling)
        leaf_size = self._leaf_size(leaf)
        if sibling_size + leaf_size <= self.node_store.node_size:
            for k, v in sibling.pairs():
                leaf.add(k, v)
            parent.remove(pairs[sibling_index][0])
            self.decrement(sibling.id)
            return True
        else:
            return False

    def remove_range(self, minkey, maxkey):
        '''Remove all keys in the given range.

        Range is inclusive.

        '''

        self._remove_range_from_index(self.root, minkey, maxkey)
        self._remove_single_index_children()

    def _remove_range_from_index(self, index, minkey, maxkey):
        new = self._shadow(index)

        getkey = lambda pair: pair[0]
        pairs = new.pairs()
        
        a, b = btree.bsearch(pairs, minkey, getkey=getkey)
        i, j = btree.bsearch(pairs, maxkey, getkey=getkey)

        partials = set()
        wholesale_low = None
        wholesale_high = None

#        assert minkey <= maxkey
#        if a is None and b is None:
#            assert i is None
#            assert j is None
#        else:
#            assert i is not None or j is not None

        if a is None and b is None:
            # Empty node, nothing to remove.
            return new
        else:
            if a is not None:
                partials.add(a)
            if b is not None:
                partials.add(b)
                if i is not None and i-b > 1:
                    wholesale_low = b+1
                    wholesale_high = i-1
            if i is not None:
                partials.add(i)
            
        # Delete those children that can be deleted completely.
        partials_keys = [getkey(pairs[x]) for x in partials]
        if wholesale_low is not None and wholesale_high is not None:
            for key, child_id in pairs[wholesale_low:wholesale_high+1]:
                self.decrement(child_id)
            new.remove_index_range(wholesale_low, wholesale_high)
        
        # At this point, the children at indexes a and j, if they exist,
        # may have some keys that are not in the range, so we couldn't delete
        # them wholesale.
        
        for key in partials_keys:
            child_id = new[key]
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
        
        getkey = lambda pair: pair[0]
        pairs = new.pairs()

        a, b = btree.bsearch(pairs, minkey, getkey=getkey)
        i, j = btree.bsearch(pairs, maxkey, getkey=getkey)

        if b is not None and i is not None:
            new.remove_index_range(b, i)
        return new

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

    def dump(self, f, msg=None): # pragma: no cover
        '''Dump tree structure to open file f.'''
        
        def dumper(node, indent):
            if isinstance(node, btree.IndexNode):
                f.write('%*sindex (id=%d)\n' % (indent*2, '', node.id))
                for key, child_id in node.pairs():
                    child = self.get_node(child_id)
                    dumper(child, indent + 1)
            else:
                assert isinstance(node, btree.LeafNode)
                f.write('%*sleaf (id=%d, len=%d):' % 
                        (indent*2, '', node.id, len(node)))
                for key, value in node.pairs():
                    f.write(' %s=%s' % (key, value))
                f.write('\n')
        
        if msg is not None:
            f.write('%s\n' % msg)
        f.write('Dumping tree %s\n' % self)
        dumper(self.root, 1)
