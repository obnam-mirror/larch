import struct

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
            self.root_id = None
        else:
            self.root_id = root_id

    def check_key_size(self, key):
        if len(key) != self.node_store.codec.key_bytes:
            raise KeySizeMismatch(key, self.node_store.codec.key_bytes)

    def new_id(self):
        '''Generate a new node identifier.'''
        return self.forest.new_id()
        
    def new_leaf(self, pairs):
        '''Create a new leaf node and keep track of it.'''
        leaf = btree.LeafNode(self.new_id(), pairs)
        self.node_store.put_node(leaf.id, self.node_store.codec.encode(leaf))
        return leaf
        
    def new_index(self, pairs):
        '''Create a new index node and keep track of it.'''
        index = btree.IndexNode(self.new_id(), pairs)
        self.node_store.put_node(index.id, self.node_store.codec.encode(index))
        for key, child_id in pairs:
            self.increment(child_id)
        return index
        
    def new_root(self, pairs):
        '''Create a new root node and keep track of it.'''
        root = self.new_index(pairs)
        self.root_id = root.id
        self.node_store.set_refcount(root.id, 1)

    def get_node(self, node_id):
        '''Return node corresponding to a node id.'''
        encoded = self.node_store.get_node(node_id)
        return self.node_store.codec.decode(encoded)

    @property
    def root(self):
        '''Return the root node.'''
        if self.root_id is None:
            return None
        else:
            return self.get_node(self.root_id)
        
    def lookup(self, key):
        '''Return value corresponding to ``key``.
        
        If the key is not in the tree, raise ``KeyError``.
        
        '''

        self.check_key_size(key)
        if self.root_id is None:
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

    def insert(self, key, value):
        '''Insert a new key/value pair into the tree.
        
        If the key already existed in the tree, the old value is silently
        forgotten.
        
        '''

        self.check_key_size(key)
        if self.root_id is None:
            self.new_root([])
        old_root_id = self.root.id
        a, b = self._insert(self.root.id, key, value)
        if b is None:
            self.new_root(a.pairs())
        else:
            self.new_root([(a.first_key(), a.id), (b.first_key(), b.id)])
        self.decrement(old_root_id)

    def _insert(self, node_id, key, value):
        node = self.get_node(node_id)
        if isinstance(node, btree.LeafNode):
            return self._insert_into_leaf(node_id, key, value)
        elif len(node) == 0:
            return self._insert_into_empty_root(key, value)
        elif len(node) == self.max_index_length:
            return self._insert_into_full_index(node_id, key, value)
        else:
            return self._insert_into_nonfull_index(node_id, key, value)

    def _insert_into_leaf(self, leaf_id, key, value):
        leaf = self.get_node(leaf_id)
        pairs = sorted(leaf.pairs(exclude=[key]) + [(key, value)])
        if self.node_store.codec.leaf_size(pairs) <= self.node_store.node_size:
            return self.new_leaf(pairs), None
        else:
            n = len(pairs) / 2
            leaf1 = self.new_leaf(pairs[:n])
            leaf2 = self.new_leaf(pairs[n:])
            return leaf1, leaf2

    def _insert_into_empty_root(self, key, value):
        leaf = self.new_leaf([(key, value)])
        return self.new_index([(leaf.first_key(), leaf.id)]), None

    def _insert_into_full_index(self, node_id, key, value):
        # A full index node needs to be split, then key/value inserted into
        # one of the halves.
        node = self.get_node(node_id)
        pairs = node.pairs()
        n = len(pairs) / 2
        node1 = self.new_index(pairs[:n])
        node2 = self.new_index(pairs[n:])
        if key < node2.first_key():
            a, b = self._insert(node1.id, key, value)
            assert b is None
            return a, node2
        else:
            a, b = self._insert(node2.id, key, value)
            assert b is None
            return node1, a
    
    def _insert_into_nonfull_index(self, node_id, key, value):        
        # Insert into correct child, get up to two replacements for
        # that child.

        node = self.get_node(node_id)
        k = node.find_key_for_child_containing(key)
        if k is None:
            k = node.first_key()

        child = self.get_node(node[k])
        a, b = self._insert(child.id, key, value)
        assert a is not None
        pairs = node.pairs(exclude=[k])
        pairs += [(a.first_key(), a.id)]
        if b is not None:
            pairs += [(b.first_key(), b.id)]
        pairs.sort()
        assert len(pairs) <= self.max_index_length
        return self.new_index(pairs), None

    def remove(self, key):
        '''Remove ``key`` and its associated value from tree.
        
        If key is not in the tree, ``KeyValue`` is raised.
        
        '''
        
        self.check_key_size(key)
        if self.root_id is None:
            raise KeyError(key)
        old_root_id = self.root.id
        a = self._remove(self.root.id, key)
        if a is None:
            self.new_root([])
        else:
            self.new_root(a.pairs())
        self.decrement(old_root_id)

    def _remove(self, node_id, key):
        node = self.get_node(node_id)
        if isinstance(node, btree.LeafNode):
            return self._remove_from_leaf(node_id, key)
        else:
            k = node.find_key_for_child_containing(key)
            if k is None:
                raise KeyError(key) # pragma: no cover
            elif len(self.get_node(node[k])) <= self.min_index_length:
                return self._remove_from_minimal_index(node_id, key, k) 
            else:
                return self._remove_from_nonminimal_index(node_id, key, k)

    def _remove_from_leaf(self, node_id, key):
        node = self.get_node(node_id)
        if key in node:
            pairs = node.pairs(exclude=[key])
            if pairs:
                return self.new_leaf(pairs)
            else:
                return None
        else:
            raise KeyError(key)
    
    def _merge(self, id1, id2):
        n1 = self.get_node(id1)
        n2 = self.get_node(id2)
        if isinstance(n1, btree.IndexNode):
            assert isinstance(n2, btree.IndexNode)
            return self.new_index(n1.pairs() + n2.pairs())
        else:
            assert isinstance(n1, btree.LeafNode)
            assert isinstance(n2, btree.LeafNode)
            return self.new_leaf(n1.pairs() + n2.pairs())

    def _remove_from_minimal_index(self, node_id, key, child_key):
        node = self.get_node(node_id)
        exclude = [child_key]
        new_ones = []
        child = self._remove(node[child_key], key)

        if child is not None:
            keys = node.keys()
            i = keys.index(child_key)

            # If possible, merge with left or right sibling.
            if (i > 0 and 
                len(self.get_node(node[keys[i-1]])) < self.max_index_length):
                new_ones.append(self._merge(node[keys[i-1]], child.id))
                exclude.append(keys[i-1])
            elif (i+1 < len(keys) and 
                  len(self.get_node(node[keys[i+1]])) < self.max_index_length):
                new_ones.append(self._merge(node[keys[i+1]], child.id))
                exclude.append(keys[i+1])
            else:
                new_ones.append(child)
        
        others = node.pairs(exclude=exclude)
        if others + new_ones:
            return self.new_index(others + 
                                  [(n.first_key(), n.id) for n in new_ones])
        else:
            return None

    def _remove_from_nonminimal_index(self, node_id, key, child_key):
        node = self.get_node(node_id)
        child = self._remove(node[child_key], key)
        pairs = node.pairs(exclude=[child_key])
        if child is not None:
            pairs += [(child.first_key(), child.id)]
        pairs.sort()
        assert pairs
        return self.new_index(pairs)

    def increment(self, node_id):
        '''Non-recursively increment refcount for a node.'''
        refcount = self.node_store.get_refcount(node_id)
        self.node_store.set_refcount(node_id, refcount + 1)

    def decrement(self, node_id): # pragma: no cover
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

