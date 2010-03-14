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


class Node(dict):

    '''Abstract base class for index and leaf nodes.
    
    A node may be initialized with a list of (key, value) pairs. For
    leaf nodes, the values are the actual values. For index nodes, they
    are references to other nodes.
    
    '''

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

    def __init__(self, pairs):
        for key, child in pairs:
            assert type(key) == str
            assert isinstance(child, IndexNode) or isinstance(child, LeafNode)
        dict.__init__(self, pairs)

    def find_key_for_child_containing(self, key):
        '''Return key for the child that contains ``key``.'''
        for k in reversed(self.keys()):
            if key >= k:
                return k
        return None
       

class BTree(object):

    '''B-tree.
    
    The tree is balanced, and has a fan-out factor given to the initializer
    as its only argument. The fan-out factor determines how aggressively
    the tree expands at each level.
    
    Three basic operations are available to the tree: lookup, insert, and
    remove.
    
    '''

    def __init__(self, fanout):
        self.root = IndexNode([])
        self.fanout = fanout
        self.min_index_length = self.fanout
        self.max_index_length = 2 * self.fanout + 1
        
    def lookup(self, key):
        '''Return value corresponding to ``key``.
        
        If the key is not in the tree, raise ``KeyError``.
        
        '''

        return self._lookup(self.root, key)

    def _lookup(self, node, key):
        if isinstance(node, LeafNode):
            return node[key]
        else:
            k = node.find_key_for_child_containing(key)
            if k is None:
                raise KeyError(key)
            else:
                return self._lookup(node[k], key)

    def insert(self, key, value):
        '''Insert a new key/value pair into the tree.
        
        If the key already existed in the tree, the old value is silently
        forgotten.
        
        '''

        a, b = self._insert(self.root, key, value)
        if b is None:
            self.root = a
        else:
            self.root = IndexNode([(a.first_key(), a),
                                   (b.first_key(), b)])

    def _insert(self, node, key, value):
        if isinstance(node, LeafNode):
            return self._insert_into_leaf(node, key, value)
        elif len(node) == 0:
            return self._insert_into_empty_root(key, value)
        elif len(node) == self.max_index_length:
            return self._insert_into_full_index(node, key, value)
        else:
            return self._insert_into_nonfull_index(node, key, value)

    def _insert_into_leaf(self, leaf, key, value):
        pairs = sorted(leaf.pairs(exclude=[key]) + [(key, value)])
        if len(pairs) <= self.fanout:
            return LeafNode(pairs), None
        else:
            n = len(pairs) / 2
            leaf1 = LeafNode(pairs[:n])
            leaf2 = LeafNode(pairs[n:])
            return leaf1, leaf2

    def _insert_into_empty_root(self, key, value):
        leaf = LeafNode([(key, value)])
        return IndexNode([(leaf.first_key(), leaf)]), None

    def _insert_into_full_index(self, node, key, value):
        # A full index node needs to be split, then key/value inserted into
        # one of the halves.
        pairs = node.pairs()
        n = len(pairs) / 2
        node1 = IndexNode(pairs[:n])
        node2 = IndexNode(pairs[n:])
        if key <  node2.first_key():
            a, b = self._insert(node1, key, value)
            assert b is None
            return a, node2
        else:
            a, b = self._insert(node2, key, value)
            assert b is None
            return node1, a
    
    def _insert_into_nonfull_index(self, node, key, value):        
        # Insert into correct child, get up to two replacements for
        # that child.

        k = node.find_key_for_child_containing(key)
        if k is None:
            k = node.first_key()

        a, b = self._insert(node[k], key, value)
        assert a is not None
        pairs = node.pairs(exclude=[k]) + [(a.first_key(), a)]
        if b is not None:
            pairs += [(b.first_key(), b)]
        pairs.sort()
        assert len(pairs) <= self.max_index_length
        return IndexNode(pairs), None

    def remove(self, key):
        '''Remove ``key`` and its associated value from tree.
        
        If key is not in the tree, ``KeyValue`` is raised.
        
        '''
        
        self.root = self._remove(self.root, key)
        if self.root is None:
            self.root = IndexNode([])
        
    def _remove(self, node, key):
        if isinstance(node, LeafNode):
            return self._remove_from_leaf(node, key)
        else:
            k = node.find_key_for_child_containing(key)
            if k is None:
                raise KeyError(key)
            elif len(node[k]) <= self.min_index_length:
                return self._remove_from_minimal_index(node, key, k) 
            else:
                return self._remove_from_nonminimal_index(node, key, k)

    def _remove_from_leaf(self, node, key):
        if key in node:
            pairs = node.pairs(exclude=[key])
            if pairs:
                return LeafNode(pairs)
            else:
                return None
        else:
            raise KeyError(key)
    
    def _merge(self, n1, n2):
        if isinstance(n1, IndexNode):
            assert isinstance(n2, IndexNode)
            return IndexNode(n1.pairs() + n2.pairs())
        else:
            assert isinstance(n1, LeafNode)
            assert isinstance(n2, LeafNode)
            return LeafNode(n1.pairs() + n2.pairs())

    def _remove_from_minimal_index(self, node, key, child_key):
        exclude = [child_key]
        new_ones = []
        child = self._remove(node[child_key], key)

        if child is not None:
            keys = node.keys()
            i = keys.index(child_key)

            # If possible, merge with left or right sibling.
            if i > 0 and len(node[keys[i-1]]) < self.max_index_length:
                new_ones.append(self._merge(node[keys[i-1]], child))
                exclude.append(keys[i-1])
            elif i+1 < len(keys) and len(node[keys[i+1]]) < self.max_index_length:
                new_ones.append(self._merge(node[keys[i+1]], child))
                exclude.append(keys[i+1])
            else:
                new_ones.append(child)
        
        others = node.pairs(exclude=exclude)
        if others + new_ones:
            return IndexNode(others + [(n.first_key(), n) for n in new_ones])
        else:
            return None

    def _remove_from_nonminimal_index(self, node, key, child_key):
        child = self._remove(node[child_key], key)
        pairs = node.pairs(exclude=[child_key])
        if child is not None:
            pairs += [(child.first_key(), child)]
        pairs.sort()
        assert pairs
        return IndexNode(pairs)
