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

    def encode(self): # pragma: no cover
        '''Encode the node as a byte string.'''
        
        return 'FIXME'


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
            assert isinstance(child, IndexNode) or isinstance(child, LeafNode)
        Node.__init__(self, node_id, pairs)

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
        self.fanout = fanout
        self.min_index_length = self.fanout
        self.max_index_length = 2 * self.fanout + 1
        self.last_id = 0
        self.nodes = dict()
        self.root = self.new_root([])

    def new_id(self):
        '''Generate a new node identifier.'''
        self.last_id += 1
        return self.last_id
        
    def new_leaf(self, pairs):
        '''Create a new leaf node and keep track of it.'''
        leaf = LeafNode(self.new_id(), pairs)
        self.nodes[leaf.id] = leaf
        return leaf
        
    def new_index(self, pairs):
        '''Create a new index node and keep track of it.'''
        index = IndexNode(self.new_id(), pairs)
        self.nodes[index.id] = index
        return index
        
    def new_root(self, pairs):
        '''Create a new root node and keep track of it.'''
        root = IndexNode(0, pairs)
        self.nodes[root.id] = root
        return root

    def get_node(self, node_id):
        '''Return node corresponding to a node id.'''
        return self.nodes[node_id]

    def get_root(self):
        '''Return the root node.'''
        return self.get_node(0)
        
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
            self.root = self.new_root([(a.first_key(), a),
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
            return self.new_leaf(pairs), None
        else:
            n = len(pairs) / 2
            leaf1 = self.new_leaf(pairs[:n])
            leaf2 = self.new_leaf(pairs[n:])
            return leaf1, leaf2

    def _insert_into_empty_root(self, key, value):
        leaf = self.new_leaf([(key, value)])
        return self.new_index([(leaf.first_key(), leaf)]), None

    def _insert_into_full_index(self, node, key, value):
        # A full index node needs to be split, then key/value inserted into
        # one of the halves.
        pairs = node.pairs()
        n = len(pairs) / 2
        node1 = self.new_index(pairs[:n])
        node2 = self.new_index(pairs[n:])
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
        return self.new_index(pairs), None

    def remove(self, key):
        '''Remove ``key`` and its associated value from tree.
        
        If key is not in the tree, ``KeyValue`` is raised.
        
        '''
        
        self.root = self._remove(self.root, key)
        if self.root is None:
            self.root = self.new_index([])
        
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
                return self.new_leaf(pairs)
            else:
                return None
        else:
            raise KeyError(key)
    
    def _merge(self, n1, n2):
        if isinstance(n1, IndexNode):
            assert isinstance(n2, IndexNode)
            return self.new_index(n1.pairs() + n2.pairs())
        else:
            assert isinstance(n1, LeafNode)
            assert isinstance(n2, LeafNode)
            return self.new_leaf(n1.pairs() + n2.pairs())

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
            return self.new_index(others + 
                                  [(n.first_key(), n) for n in new_ones])
        else:
            return None

    def _remove_from_nonminimal_index(self, node, key, child_key):
        child = self._remove(node[child_key], key)
        pairs = node.pairs(exclude=[child_key])
        if child is not None:
            pairs += [(child.first_key(), child)]
        pairs.sort()
        assert pairs
        return self.new_index(pairs)


class NodeMissing(Exception): # pragma: no cover

    '''A node cannot be found from a NodeStore.'''
    
    def __init__(self, node_id):
        self.node_id = node_id
        
    def __str__(self):
        return 'Node %d cannot be found in the node store' % self.node_id


class NodeTooBig(Exception): # pragma: no cover

    '''User tried to put a node that was too big into the store.'''
    
    def __init__(self, node_id, node_size):
        self.node_id = node_id
        self.node_size = node_size
        
    def __str__(self):
        return 'Node %d is too big (%d bytes)' % (self.node_id, self.node_size)
        
        
class NodeExists(Exception): # pragma: no cover

    '''User tried to put a node that already exists in the store.'''
    
    def __init__(self, node_id):
        self.node_id = node_id
        
    def __str__(self):
        return 'Node %d is already in the store' % self.node_id
        
        
class NodeStore(object): # pragma: no cover

    '''Abstract base class for storing nodes externally.
    
    The BTree class itself does not handle external storage of nodes.
    Instead, it is given an object that implements the API in this
    class. An actual implementation might keep nodes in memory, or
    store them on disk using a filesystem, or a database.
    
    Node stores deal with nodes as byte strings: the BTree class
    encodes them before handing them to the store, and decodes them
    when it gets them from the store.
    
    Each node has an identifier that is unique within the tree.
    The identifier is an integer, and the BTree makes the following
    guarantees about it:
    
    * it is a non-negative integer
    * new nodes are assigned the next consecutive one
    * it is never re-used
    
    Further, the BTree makes the following guarantees about the encoded
    nodes:
    
    * they have a strict upper size limit
    * the tree attempts to fill nodes as close to the limit as possible
    
    The size limit is given to the node store at initialization time.
    It is accessible via the node_size property. Implementations of
    this API must handle that in some suitable way, preferably by 
    inheriting from this class and calling its initializer.
    
    '''
    
    def __init__(self, node_size):
        self.node_size = node_size
        
    def put_node(self, node_id, encoded_node):
        '''Put a new node into the store.'''
        
    def get_node(self, node_id):
        '''Return a node from the store.
        
        Raise the NodeMissing exception if the node is not in the
        store (has never been, or has been removed). Raise other
        errors as suitable.
        
        '''
        
    def remove_node(self, node_id):
        '''Remove a node from the store.'''
        
    def list_nodes(self):
        '''Return list of ids of all nodes in store.'''


class NodeStoreTests(object): # pragma: no cover

    '''Re-useable tests for NodeStore implementations.
    
    The NodeStore base class can't be usefully instantiated itself.
    Instead you are supposed to sub-class it and implement the API in
    a suitable way for yourself.
    
    This class implements a number of tests that the API implementation
    must pass. The implementation's own test class should inherit from
    this class, and unittest.TestCase.
    
    The test sub-class should define a setUp method that sets the following:
    
    * self.ns to an instance of the API implementation sub-class
    * self.node_size to the node size
    
    '''
    
    def test_sets_node_size(self):
        self.assertEqual(self.ns.node_size, self.node_size)
        
    def test_has_no_node_zero_initially(self):
        self.assertRaises(NodeMissing, self.ns.get_node, 0)

    def test_lists_no_nodes_initially(self):
        self.assertEqual(self.ns.list_nodes(), [])
        
    def test_puts_and_gets_same(self):
        encoded = LeafNode(0).encode()
        self.ns.put_node(0, encoded)
        self.assertEqual(self.ns.get_node(0), encoded)

    def test_removes_node(self):
        encoded = LeafNode(0).encode()
        self.ns.put_node(0, encoded)
        self.ns.remove_node(0)
        self.assertRaises(NodeMissing, self.ns.get_node, 0)
        self.assertEqual(self.ns.list_nodes(), [])

    def test_lists_node_zero(self):
        encoded = LeafNode(0).encode()
        self.ns.put_node(0, encoded)
        self.assertEqual(self.ns.list_nodes(), [0])

    def test_put_refuses_too_large_a_node(self):
        self.assertRaises(NodeTooBig, self.ns.put_node, 0, 
                          'x' * (self.node_size + 1))

    def test_put_refuses_to_overwrite_a_node(self):
        encoded = 'x'
        self.ns.put_node(0, encoded)
        self.assertRaises(NodeExists, self.ns.put_node, 0, encoded)

    def test_remove_raises_nodemissing_if_node_does_not_exist(self):
        self.assertRaises(NodeMissing, self.ns.remove_node, 0)
