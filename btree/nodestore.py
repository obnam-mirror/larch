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


import btree


class NodeMissing(Exception): # pragma: no cover

    '''A node cannot be found from a NodeStore.'''
    
    def __init__(self, node_id):
        self.node_id = node_id
        
    def __str__(self):
        return 'Node %d cannot be found in the node store' % self.node_id


class NodeTooBig(Exception): # pragma: no cover

    '''User tried to put a node that was too big into the store.'''
    
    def __init__(self, node, node_size):
        self.node_type = node.__class__.__name__
        self.node_id = node.id
        self.node_size = node_size
        
    def __str__(self):
        return ('%s %d is too big (%d bytes)' % 
                (self.node_type, self.node_id, self.node_size))
        
        
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

    A node store additionally stores some metadata, as key/value
    pairs, where both key and value is a shortish string. The whole
    pair must fit into a node, but more than one node can be used for
    metadata.
    
    '''
    
    def __init__(self, node_size, codec):
        self.node_size = node_size
        self.codec = codec
        self.max_value_size = (node_size / 2) - codec.leaf_header.size

    def max_index_pairs(self):
        return self.codec.max_index_pairs(self.node_size)
        
    def set_metadata(self, key, value):
        '''Set a metadata key/value pair.'''
        
    def get_metadata(self, key):
        '''Return value that corresponds to a key.'''

    def get_metadata_keys(self):
        '''Return list of all metadata keys.'''

    def remove_metadata(self, key):
        '''Remove a metadata key, and its corresponding value.'''

    def save_metadata(self):
        '''Save metadata persistently, if applicable.

        Not all node stores are persistent, and this method is
        not relevant to them. However, if the user does not call
        this method, none of the changes they make will be stored
        persistently even with a persistent store.

        '''
        
    def put_node(self, node):
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

    def push_upload_queue(self):
        '''Make sure all changes to nodes have been uploaded.'''

    def get_refcount(self, node_id):
        '''Return the reference count for a node.'''

    def set_refcount(self, node_id, refcount):
        '''Set the reference count for a node.'''

    def save_refcounts(self):
        '''Save refcounts to disk.

        This method only applies to node stores that persist.

        '''


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
    
    key_bytes = 3

    def assertEqualNodes(self, n1, n2):
        '''Assert that two nodes are equal.

        Equal means same keys, and same values for keys. Nodes can be
        either leaf or index ones.

        '''

        self.assertEqual(sorted(n1.keys()), sorted(n2.keys()))
        for key in n1:
            self.assertEqual(n1[key], n2[key])
    
    def test_sets_node_size(self):
        self.assertEqual(self.ns.node_size, self.node_size)
        
    def test_sets_max_value_size(self):
        self.assert_(self.ns.max_value_size > 1)
        self.assert_(self.ns.max_value_size < self.node_size / 2)

    def test_has_no_metadata_initially(self):
        self.assertEqual(self.ns.get_metadata_keys(), [])
        
    def test_sets_metadata(self):
        self.ns.set_metadata('foo', 'bar')
        self.assertEqual(self.ns.get_metadata_keys(), ['foo'])
        self.assertEqual(self.ns.get_metadata('foo'), 'bar')
        
    def test_sets_existing_metadata(self):
        self.ns.set_metadata('foo', 'bar')
        self.ns.set_metadata('foo', 'foobar')
        self.assertEqual(self.ns.get_metadata_keys(), ['foo'])
        self.assertEqual(self.ns.get_metadata('foo'), 'foobar')

    def test_removes_metadata(self):
        self.ns.set_metadata('foo', 'bar')
        self.ns.remove_metadata('foo')
        self.assertEqual(self.ns.get_metadata_keys(), [])

    def test_sets_several_metadata_keys(self):
        pairs = dict(('%d' % i, '%0128d' % i) for i in range(1024))
        for key, value in pairs.iteritems():
            self.ns.set_metadata(key, value)
        self.assertEqual(sorted(self.ns.get_metadata_keys()), 
                         sorted(pairs.keys()))
        for key, value in pairs.iteritems():
            self.assertEqual(self.ns.get_metadata(key), value)

    def test_raises_error_when_getting_unknown_key(self):
        self.assertRaises(KeyError, self.ns.get_metadata, 'foo')

    def test_raises_error_when_removing_unknown_key(self):
        self.assertRaises(KeyError, self.ns.remove_metadata, 'foo')

    def test_has_no_node_zero_initially(self):
        self.assertRaises(NodeMissing, self.ns.get_node, 0)

    def test_lists_no_nodes_initially(self):
        self.assertEqual(self.ns.list_nodes(), [])
        
    def test_puts_and_gets_same(self):
        node = btree.LeafNode(0, [], [])
        self.ns.put_node(node)
        self.ns.push_upload_queue()
        self.assertEqualNodes(self.ns.get_node(0), node)

    def test_put_freezes_node(self):
        node = btree.LeafNode(0, [], [])
        self.ns.put_node(node)
        self.assert_(node.frozen)

    def test_get_freezes_node(self):
        node = btree.LeafNode(0, [], [])
        self.ns.put_node(node)
        node2 = self.ns.get_node(0)
        self.assert_(node2.frozen)

    def test_removes_node(self):
        node = btree.LeafNode(0, [], [])
        self.ns.put_node(node)
        self.ns.push_upload_queue()
        self.ns.remove_node(0)
        self.assertRaises(NodeMissing, self.ns.get_node, 0)
        self.assertEqual(self.ns.list_nodes(), [])

    def test_removes_node_from_upload_queue_if_one_exists(self):
        node = btree.LeafNode(0, [], [])
        self.ns.put_node(node)
        self.ns.remove_node(0)
        self.assertRaises(NodeMissing, self.ns.get_node, 0)
        self.assertEqual(self.ns.list_nodes(), [])

    def test_lists_node_zero(self):
        node = btree.LeafNode(0, [], [])
        self.ns.put_node(node)
        self.ns.push_upload_queue()
        node_ids = self.ns.list_nodes()
        self.assertEqual(node_ids, [node.id])

    def test_put_allows_to_overwrite_a_node(self):
        node = btree.LeafNode(0, [], [])
        self.ns.put_node(node)
        node = btree.LeafNode(0, ['foo'], ['bar'])
        self.ns.put_node(node)
        new = self.ns.get_node(0)
        self.assertEqual(new.keys(), ['foo'])
        self.assertEqual(new.values(), ['bar'])

    def test_put_allows_to_overwrite_a_node_after_upload_queue_push(self):
        node = btree.LeafNode(0, [], [])
        self.ns.put_node(node)
        self.ns.push_upload_queue()
        node = btree.LeafNode(0, ['foo'], ['bar'])
        self.ns.put_node(node)
        self.ns.push_upload_queue()
        new = self.ns.get_node(0)
        self.assertEqual(new.keys(), ['foo'])
        self.assertEqual(new.values(), ['bar'])

    def test_remove_raises_nodemissing_if_node_does_not_exist(self):
        self.assertRaises(NodeMissing, self.ns.remove_node, 0)

    def test_returns_zero_count_for_unknown_node_id(self):
        self.assertEqual(self.ns.get_refcount(123), 0)

    def test_sets_refcount(self):
        self.ns.set_refcount(0, 123)
        self.assertEqual(self.ns.get_refcount(0), 123)

    def test_updates_refcount(self):
        self.ns.set_refcount(0, 123)
        self.ns.set_refcount(0, 0)
        self.assertEqual(self.ns.get_refcount(0), 0)

