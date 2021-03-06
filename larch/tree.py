# Copyright 2010, 2011  Lars Wirzenius
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
import tracing

import larch


'''A simple B-tree implementation.'''


class KeySizeMismatch(larch.Error):

    '''User tried to use key of wrong size.'''

    def __init__(self, key, wanted_size):
        self.msg = ('Key %s is of wrong length (%d, should be %d)' %
                    (repr(key), len(key), wanted_size))


class ValueTooLarge(larch.Error):

    '''User tried ot use a vlaue htat is too large for a node.'''

    def __init__(self, value, max_size):
        self.msg = ('Value %s is too long (%d, max %d)' %
                    (repr(value), len(value), max_size))
       

class BTree(object):

    '''A balanced search tree (copy-on-write B-tree).
    
    The tree belongs to a forest. The tree nodes are stored in an 
    external node store; see the ``NodeStore`` class.
    
    ``root_id`` gives the id of the root node of the tree. The
    root node must be unique to this tree, as it is modified in
    place. ``root_id`` may also be ``None``, in which case a
    new node is created automatically to serve as the root node.
    
    '''

    def __init__(self, forest, node_store, root_id):
        self.forest = forest
        self.node_store = node_store

        self.max_index_length = self.node_store.max_index_pairs()
        self.min_index_length = self.max_index_length / 2

        if root_id is None:
            self.root = None
        else:
            self.root = self._get_node(root_id)
            
        tracing.trace('init BTree %s with root_id %s' % (self, root_id))

    def _check_key_size(self, key):
        if len(key) != self.node_store.codec.key_bytes:
            raise KeySizeMismatch(key, self.node_store.codec.key_bytes)

    def _check_value_size(self, value):
        if len(value) > self.node_store.max_value_size:
            raise ValueTooLarge(value, self.node_store.max_value_size)

    def _new_id(self):
        '''Generate a new node identifier.'''
        return self.forest.new_id()
    
    def _new_leaf(self, keys, values):
        '''Create a new leaf node.'''
        node = larch.LeafNode(self._new_id(), keys, values)
        tracing.trace('id=%s' % node.id)
        return node
        
    def _new_index(self, keys, values):
        '''Create a new index node.'''
        index = larch.IndexNode(self._new_id(), keys, values)
        for child_id in values:
            self._increment(child_id)
        tracing.trace('id=%s' % index.id)
        return index

    def _set_root(self, new_root):
        '''Replace existing root node.'''
        tracing.trace('new_root.id=%s' % new_root.id)
        if self.root is not None and self.root.id != new_root.id:
            tracing.trace('decrement old root %s' % self.root.id)
            self._decrement(self.root.id)
        self._put_node(new_root)
        self.root = new_root
        tracing.trace('setting node %s refcount to 1' % self.root.id)
        self.node_store.set_refcount(self.root.id, 1)
        
    def _get_node(self, node_id):
        '''Return node corresponding to a node id.'''
        return self.node_store.get_node(node_id)

    def _put_node(self, node):
        '''Put node into node store.'''
        tracing.trace('node.id=%s' % node.id)
        return self.node_store.put_node(node)

    def _leaf_size(self, node):
        if node.size is None:
            node.size = self.node_store.codec.leaf_size(node.keys(), 
                                                        node.values())
        return node.size

    def lookup(self, key):
        '''Return value corresponding to ``key``.
        
        If the key is not in the tree, raise ``KeyError``.
        
        '''

        tracing.trace('looking up %s' % repr(key))
        tracing.trace('tree is %s (root id %s)',
                      self, self.root.id if self.root else None)
        self._check_key_size(key)

        node = self.root
        while isinstance(node, larch.IndexNode):
            k = node.find_key_for_child_containing(key)
            # If k is None, then the indexing of node will cause KeyError
            # to be returned, just like we want to. This saves us from
            # having to test for it separately.
            node = self._get_node(node[k])
            
        if isinstance(node, larch.LeafNode):
            return node[key]

        raise KeyError(key)

    def lookup_range(self, minkey, maxkey):
        '''Return list of (key, value) pairs for all keys in a range.

        ``minkey`` and ``maxkey`` are included in range.

        '''

        tracing.trace('looking up range %s .. %s' % 
                        (repr(minkey), repr(maxkey)))
        tracing.trace('tree is %s (root id %s)',
                      self, self.root.id if self.root else None)
        self._check_key_size(minkey)
        self._check_key_size(maxkey)
        if self.root is None:
            return []
        else:
            return [pair 
                     for pair in 
                        self._lookup_range(self.root.id, minkey, maxkey)]

    def _lookup_range(self, node_id, minkey, maxkey):
        node = self._get_node(node_id)
        if isinstance(node, larch.LeafNode):
            for key in node.find_keys_in_range(minkey, maxkey):
                yield key, node[key]
        else:
            assert isinstance(node, larch.IndexNode)
            result = []
            for child_id in node.find_children_in_range(minkey, maxkey):
                for pair in self._lookup_range(child_id, minkey, maxkey):
                    yield pair

    def count_range(self, minkey, maxkey):
        '''Return number of keys in range.'''

        tracing.trace('count_range(%s, %s)' % (repr(minkey), repr(maxkey)))
        tracing.trace('tree is %s (root id %s)',
                      self, self.root.id if self.root else None)
        self._check_key_size(minkey)
        self._check_key_size(maxkey)

        if self.root is None:
            return 0

        return self._count_range(self.root.id, minkey, maxkey)

    def _count_range(self, node_id, minkey, maxkey):
        node = self._get_node(node_id)
        if isinstance(node, larch.LeafNode):
            return len(list(node.find_keys_in_range(minkey, maxkey)))
        else:
            assert isinstance(node, larch.IndexNode)
            count = 0
            for child_id in node.find_children_in_range(minkey, maxkey):
                count += self._count_range(child_id, minkey, maxkey)
            return count

    def range_is_empty(self, minkey, maxkey):
        '''Is a range empty in the tree?
        
        This is faster than doing a range lookup for the same range,
        and checking if there are any keys returned.
        
        '''

        tracing.trace('range_is_empty(%s, %s)' % (repr(minkey), repr(maxkey)))
        tracing.trace('tree is %s (root id %s)',
                      self, self.root.id if self.root else None)
        self._check_key_size(minkey)
        self._check_key_size(maxkey)
        if self.root is None:
            return True
        return self._range_is_empty(self.root.id, minkey, maxkey)

    def _range_is_empty(self, node_id, minkey, maxkey):
        node = self._get_node(node_id)
        if isinstance(node, larch.LeafNode):
            return node.find_keys_in_range(minkey, maxkey) == []
        else:
            assert isinstance(node, larch.IndexNode)
            for child_id in node.find_children_in_range(minkey, maxkey):
                if not self._range_is_empty(child_id, minkey, maxkey):
                    return False
            return True

    def _shadow(self, node):
        '''Shadow a node: make it possible to modify it in-place.'''

        tracing.trace('node.id=%s' % node.id)
        if self.node_store.can_be_modified(node):
            tracing.trace('can be modified in place')
            self.node_store.start_modification(node)
            new = node
        elif isinstance(node, larch.IndexNode):
            tracing.trace('new index node')
            new = self._new_index(node.keys(), node.values())
        else:
            tracing.trace('new leaf node')
            new = self._new_leaf(node.keys(), node.values())
            new.size = node.size
        tracing.trace('returning new.id=%s' % new.id)
        return new
        
    def insert(self, key, value):
        '''Insert a new key/value pair into the tree.
        
        If the key already existed in the tree, the old value is silently
        forgotten.
        
        '''

        tracing.trace('key=%s' % repr(key))
        tracing.trace('value=%s' % repr(value))
        tracing.trace('tree is %s (root id %s)',
                      self, self.root.id if self.root else None)
        self._check_key_size(key)
        self._check_value_size(value)

        # Is the tree empty? This needs special casing to keep
        # _insert_into_index simpler.
        if self.root is None or len(self.root) == 0:
            tracing.trace('tree is empty')
            leaf = self._new_leaf([key], [value])
            self._put_node(leaf)
            if self.root is None:
                new_root = self._new_index([key], [leaf.id])
            else:
                new_root = self._shadow(self.root)
                new_root.add(key, leaf.id)
                self._increment(leaf.id)
        else:
            tracing.trace('tree is not empty')
            kids = self._insert_into_index(self.root, key, value)
            # kids contains either one or more index nodes. If one,
            # we use that as the new root. Otherwise, we create a new one,
            # making the tree higher because we must.
            assert len(kids) > 0
            for kid in kids:
                assert type(kid) == larch.IndexNode
            if len(kids) == 1:
                new_root = kids[0]
                tracing.trace('only one kid: id=%s' % new_root.id)
            else:
                keys = [kid.first_key() for kid in kids]
                values = [kid.id for kid in kids]
                new_root = self._new_index(keys, values)
                tracing.trace('create new root: id=%s' % new_root.id)

        self._set_root(new_root)

    def _insert_into_index(self, old_index, key, value):
        '''Insert key, value into an index node.
        
        Return list of replacement nodes. Might be just the same node,
        or a single new node, or two nodes, one of which might be the
        same node. Note that this method never makes the tree higher,
        that is the job of the caller. If two nodes are returned,
        they are siblings at the same height as the original node.
        
        '''

        tracing.trace('old_index.id=%s' % old_index.id)
        new_index = self._shadow(old_index)

        child_key = new_index.find_key_for_child_containing(key)
        if child_key is None:
            child_key = new_index.first_key()

        child = self._get_node(new_index[child_key])
        if isinstance(child, larch.IndexNode):
            new_kids = self._insert_into_index(child, key, value)
        else:
            new_kids = self._insert_into_leaf(child, key, value)

        new_index.remove(child_key)
        do_dec = True
        for kid in new_kids:
            new_index.add(kid.first_key(), kid.id)
            if kid.id != child.id:
                self._increment(kid.id)
            else:
                do_dec = False
        if do_dec: # pragma: no cover
            self._decrement(child.id)

        if len(new_index) > self.max_index_length:
            tracing.trace('need to split index node id=%s' % new_index.id)
            n = len(new_index) / 2
            keys = new_index.keys()[n:]
            values = new_index.values()[n:]
            new = larch.IndexNode(self._new_id(), keys, values)
            tracing.trace('new index node id=%s' % new.id)
            new_index.remove_index_range(n, len(new_index))
            self._put_node(new_index)
            self._put_node(new)
            return [new_index, new]
        else:
            tracing.trace('no need to split index node id=%s' % new_index.id)
            self._put_node(new_index)
            return [new_index]

    def _insert_into_leaf(self, leaf, key, value):
        '''Insert a key/value pair into a leaf node.
        
        Return value is like for _insert_into_index.
        
        '''
        
        tracing.trace('leaf.id=%s' % leaf.id)

        codec = self.node_store.codec
        max_size = self.node_store.node_size
        size = self._leaf_size

        new = self._shadow(leaf)
        old_size = size(new)
        if key in new:
            old_value = new[key]
            new.add(key, value)
            new.size = codec.leaf_size_delta_replace(old_size, old_value, 
                                                     value)
        else:
            new.add(key, value)
            new.size = codec.leaf_size_delta_add(old_size, value)


        if size(new) <= max_size:
            tracing.trace('leaf did not grow too big')
            leaves = [new]
        else:
            tracing.trace('leaf grew too big, splitting')
            keys = new.keys()
            values = new.values()

            n = len(keys) / 2
            new2 = self._new_leaf(keys[n:], values[n:])
            for key in new2:
                new.remove(key)
            if size(new2) > max_size: # pragma: no cover
                while size(new2) > max_size:
                    key = new2.keys()[0]
                    new.add(key, new2[key])
                    new2.remove(key)
            elif size(new) > max_size: # pragma: no cover
                while size(new) > max_size:
                    key = new.keys()[-1]
                    new2.add(key, new[key])
                    new.remove(key)

            leaves = [new, new2]

        for x in leaves:
            self._put_node(x)
        return leaves

    def remove(self, key):
        '''Remove ``key`` and its associated value from tree.
        
        If key is not in the tree, ``KeyValue`` is raised.
        
        '''

        tracing.trace('key=%s' % repr(key))    
        tracing.trace('tree is %s (root id %s)',
                      self, self.root.id if self.root else None)
        self._check_key_size(key)

        if self.root is None:
            tracing.trace('no root')
            raise KeyError(key)

        new_root = self._remove_from_index(self.root, key)
        self._set_root(new_root)
        self._reduce_height()

    def _remove_from_index(self, old_index, key):
        tracing.trace('old_index.id=%s' % old_index.id)
        tracing.trace('tree is %s (root id %s)',
                      self, self.root.id if self.root else None)
        child_key = old_index.find_key_for_child_containing(key)
        new_index = self._shadow(old_index)
        child = self._get_node(new_index[child_key])
        
        if isinstance(child, larch.IndexNode):
            new_kid = self._remove_from_index(child, key)
            new_index.remove(child_key)
            if len(new_kid) > 0:
                self._add_or_merge_index(new_index, new_kid)
            else:
                if new_kid.id != child.id: # pragma: no cover
                    self._decrement(new_kid.id)
            self._decrement(child.id)
        else:
            assert isinstance(child, larch.LeafNode)
            leaf = self._shadow(child)
            leaf.remove(key)
            self._put_node(leaf)
            new_index.remove(child_key)
            if len(leaf) > 0:
                self._add_or_merge_leaf(new_index, leaf)
            else:
                tracing.trace('new leaf is empty, forgetting it')
                if leaf.id != child.id: # pragma: no cover
                    self._decrement(leaf.id)
            self._decrement(child.id)

        self._put_node(new_index)
        return new_index
        
    def _add_or_merge_index(self, parent, index):
        self._add_or_merge(parent, index, self._merge_index)

    def _add_or_merge_leaf(self, parent, leaf):
        self._add_or_merge(parent, leaf, self._merge_leaf)

    def _add_or_merge(self, parent, node, merge):
        assert not parent.frozen
        assert node.frozen

        keys = parent.keys()
        
        key = node.first_key()
        i = bisect.bisect_left(keys, key)
        
        new_node = None
        if i > 0:
            new_node = merge(parent, node, i-1)
        if new_node is None and i < len(keys):
            new_node = merge(parent, node, i)
        if new_node is None:
            new_node = node

        assert new_node is not None
        self._put_node(new_node)
        parent.add(new_node.first_key(), new_node.id)
        self._increment(new_node.id)
        if new_node != node: # pragma: no cover
            # We made a new node, so get rid of the old one.
            tracing.trace('decrementing unused node id=%s' % node.id)
            self._decrement(node.id)

    def _merge_index(self, parent, node, sibling_index):

        def merge_indexes_p(a, b):
            return len(a) + len(b) <= self.max_index_length

        def add_to_index(n, k, v):
            n.add(k, v)
            self._increment(v)

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
        sibling_key = parent.keys()[sibling_index]
        sibling_id = parent[sibling_key]
        sibling = self._get_node(sibling_id)
        if merge_p(node, sibling):
            tracing.trace('merging nodes %s and %s' % (node.id, sibling.id))
            new_node = self._shadow(node)
            for k in sibling:
                add(new_node, k, sibling[k])
            self._put_node(new_node)
            parent.remove(sibling_key)
            tracing.trace('decrementing now-unused sibling %s' % sibling.id)
            self._decrement(sibling.id)
            return new_node
        else:
            return None

    def remove_range(self, minkey, maxkey):
        '''Remove all keys in the given range.

        Range is inclusive.

        '''

        tracing.trace('minkey=%s maxkey=%s' % (repr(minkey), repr(maxkey)))
        tracing.trace('tree is %s (root id %s)',
                      self, self.root.id if self.root else None)
        self._check_key_size(minkey)
        self._check_key_size(maxkey)
        keys = [k for k, v in self.lookup_range(minkey, maxkey)]
        for key in keys:
            self.remove(key)

    def _reduce_height(self):
        # After removing things, the top of the tree might consist of a
        # list of index nodes with only a single child, which is also
        # an index node. These can and should be removed, for efficiency.
        # Further, since we've modified all of these nodes, they can all
        # be modified in place.
        tracing.trace('start reducing height')
        while len(self.root) == 1:
            tracing.trace('self.root.id=%s' % self.root.id)
            key = self.root.first_key()
            child_id = self.root[key]
            assert self.node_store.get_refcount(self.root.id) == 1
            
            if self.node_store.get_refcount(child_id) != 1:
                tracing.trace('only child is shared')
                break

            child = self._get_node(child_id)
            if isinstance(child, larch.LeafNode):
                tracing.trace('only child is a leaf node')
                break

            # We can just make the child be the new root node.
            assert type(child) == larch.IndexNode
            # Prevent child from getting removed when parent's refcount
            # gets decremented. set_root will set the refcount to be 1.
            tracing.trace('setting node %s refcount to 2' % child.id)
            self.node_store.set_refcount(child.id, 2)
            self._set_root(child)
        tracing.trace('done reducing height')

    def _increment(self, node_id):
        '''Non-recursively increment refcount for a node.'''
        refcount = self.node_store.get_refcount(node_id)
        refcount += 1
        self.node_store.set_refcount(node_id, refcount)
        tracing.trace('node %s refcount grew to %s' % (node_id, refcount))

    def _decrement(self, node_id):
        '''Recursively, lazily decrement refcounts for a node and children.'''
        tracing.trace('decrementing node %s refcount' % node_id)
        refcount = self.node_store.get_refcount(node_id)
        if refcount > 1:
            refcount -= 1
            self.node_store.set_refcount(node_id, refcount)
            tracing.trace('node %s refcount now %s' % (node_id, refcount))
        else:
            tracing.trace('node %s refcount %s, removing node' % 
                         (node_id, refcount))
            node = self._get_node(node_id)
            if isinstance(node, larch.IndexNode):
                tracing.trace('reducing refcounts for children')
                for child_id in node.values():
                    self._decrement(child_id)
            self.node_store.remove_node(node_id)
            self.node_store.set_refcount(node_id, 0)

