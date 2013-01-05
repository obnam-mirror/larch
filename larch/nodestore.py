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


import larch


class NodeMissing(larch.Error):

    '''A node cannot be found from a NodeStore.'''
    
    def __init__(self, node_store, node_id, error=None):
        if error is None:
            error_msg = ''
        else:
            error_msg = (': %s: %s: %s' % 
                         (error.errno, error.strerror, error.filename))
        self.msg = ('Node %s cannot be found in the node store %s%s' % 
                    (hex(node_id), node_store, error_msg))


class NodeTooBig(larch.Error):

    '''User tried to put a node that was too big into the store.'''
    
    def __init__(self, node, node_size):
        self.msg = ('%s %s is too big (%d bytes)' % 
                    (node.__class__.__name__, hex(node.id), node_size))
        
        
class NodeExists(larch.Error):

    '''User tried to put a node that already exists in the store.'''
    
    def __init__(self, node_id):
        self.msg = 'Node %s is already in the store' % hex(node_id)
        
        
class NodeCannotBeModified(larch.Error):

    '''User called start_modification on node that cannot be modified.'''
    
    def __init__(self, node_id):
        self.msg = 'Node %s cannot be modified' % hex(node_id)
        
        
class NodeStore(object): # pragma: no cover

    '''Abstract base class for storing nodes externally.
    
    The ``BTree`` class itself does not handle external storage of nodes.
    Instead, it is given an object that implements the API in this
    class. An actual implementation might keep nodes in memory, or
    store them on disk using a filesystem, or a database.
    
    Node stores deal with nodes as byte strings: the ``codec``
    encodes them before handing them to the store, and decodes them
    when it gets them from the store.
    
    Each node has an identifier that is unique within the store.
    The identifier is an integer, and the caller makes the following
    guarantees about it:
    
    * it is a non-negative integer
    * new nodes are assigned the next consecutive one
    * it is never re-used
    
    Further, the caller makes the following guarantees about the encoded
    nodes:
    
    * they have a strict upper size limit
    * the tree attempts to fill nodes as close to the limit as possible
    
    The size limit is given to the node store at initialization time.
    It is accessible via the ``node_size`` property. Implementations of
    this API must handle that in some suitable way, preferably by 
    inheriting from this class and calling its initializer.
    
    ``self.max_value_size`` gives the maximum size of a value stored
    in a node.

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
        '''Max number of index pairs in an index node.'''
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
        
        Raise the ``NodeMissing`` exception if the node is not in the
        store (has never been, or has been removed). Raise other
        errors as suitable.
        
        '''

    def can_be_modified(self, node):
        '''Can a node be modified?'''
        return self.get_refcount(node.id) == 1
        
    def start_modification(self, node):
        '''Start modification of a node.
        
        User must call this before modifying a node in place.
        
        If a node cannot be modified, ``NodeCannotBeModified`` exception
        will be raised.
        
        '''
        
    def remove_node(self, node_id):
        '''Remove a node from the store.'''
        
    def list_nodes(self):
        '''Return list of ids of all nodes in store.'''

    def get_refcount(self, node_id):
        '''Return the reference count for a node.'''

    def set_refcount(self, node_id, refcount):
        '''Set the reference count for a node.'''

    def save_refcounts(self):
        '''Save refcounts to disk.

        This method only applies to node stores that persist.

        '''

    def commit(self):
        '''Make sure all changes to are committed to the store.
        
        Until this is called, there's no guarantee that any of the
        changes since the previous commit are persistent.
        
        '''


class NodeStoreTests(object): # pragma: no cover

    '''Re-useable tests for ``NodeStore`` implementations.
    
    The ``NodeStore`` base class can't be usefully instantiated itself.
    Instead you are supposed to sub-class it and implement the API in
    a suitable way for yourself.
    
    This class implements a number of tests that the API implementation
    must pass. The implementation's own test class should inherit from
    this class, and ``unittest.TestCase``.
    
    The test sub-class should define a setUp method that sets the following:
    
    * ``self.ns`` to an instance of the API implementation sub-class
    * ``self.node_size`` to the node size
    
    Key size (``self.key_bytes``) is always 3.
    
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

    def test_sets_metadata(self):
        self.ns.set_metadata('foo', 'bar')
        self.assert_('foo' in self.ns.get_metadata_keys())
        self.assertEqual(self.ns.get_metadata('foo'), 'bar')
        
    def test_sets_existing_metadata(self):
        self.ns.set_metadata('foo', 'bar')
        self.ns.set_metadata('foo', 'foobar')
        self.assert_('foo' in self.ns.get_metadata_keys())
        self.assertEqual(self.ns.get_metadata('foo'), 'foobar')

    def test_removes_metadata(self):
        self.ns.set_metadata('foo', 'bar')
        self.ns.remove_metadata('foo')
        self.assert_('foo' not in self.ns.get_metadata_keys())

    def test_sets_several_metadata_keys(self):
        old_keys = self.ns.get_metadata_keys()
        pairs = dict(('%d' % i, '%0128d' % i) for i in range(1024))
        for key, value in pairs.iteritems():
            self.ns.set_metadata(key, value)
        self.assertEqual(sorted(self.ns.get_metadata_keys()), 
                         sorted(pairs.keys() + old_keys))
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
        node = larch.LeafNode(0, [], [])
        self.ns.put_node(node)
        self.ns.commit()
        self.assertEqualNodes(self.ns.get_node(0), node)

    def test_put_freezes_node(self):
        node = larch.LeafNode(0, [], [])
        self.ns.put_node(node)
        self.assert_(node.frozen)

    def test_get_freezes_node(self):
        node = larch.LeafNode(0, [], [])
        self.ns.put_node(node)
        node2 = self.ns.get_node(0)
        self.assert_(node2.frozen)

    def test_node_not_in_store_can_not_be_modified(self):
        node = larch.LeafNode(0, [], [])
        self.assertFalse(self.ns.can_be_modified(node))

    def test_node_with_refcount_0_can_not_be_modified(self):
        node = larch.LeafNode(0, [], [])
        self.ns.put_node(node)
        self.ns.set_refcount(node.id, 0)
        self.assertFalse(self.ns.can_be_modified(node))

    def test_node_with_refcount_1_can_be_modified(self):
        node = larch.LeafNode(0, [], [])
        self.ns.put_node(node)
        self.ns.set_refcount(node.id, 1)
        self.assertTrue(self.ns.can_be_modified(node))

    def test_node_with_refcount_2_can_not_be_modified(self):
        node = larch.LeafNode(0, [], [])
        self.ns.put_node(node)
        self.ns.set_refcount(node.id, 2)
        self.assertFalse(self.ns.can_be_modified(node))

    def test_unfreezes_node_when_modification_starts(self):
        node = larch.LeafNode(0, [], [])
        self.ns.put_node(node)
        self.ns.set_refcount(node.id, 1)
        self.ns.start_modification(node)
        self.assertFalse(node.frozen)

    def test_removes_node(self):
        node = larch.LeafNode(0, [], [])
        self.ns.put_node(node)
        self.ns.commit()
        self.ns.remove_node(0)
        self.assertRaises(NodeMissing, self.ns.get_node, 0)
        self.assertEqual(self.ns.list_nodes(), [])

    def test_removes_node_from_upload_queue_if_one_exists(self):
        node = larch.LeafNode(0, [], [])
        self.ns.put_node(node)
        self.ns.remove_node(0)
        self.assertRaises(NodeMissing, self.ns.get_node, 0)
        self.assertEqual(self.ns.list_nodes(), [])

    def test_lists_node_zero(self):
        node = larch.LeafNode(0, [], [])
        self.ns.put_node(node)
        self.ns.commit()
        node_ids = self.ns.list_nodes()
        self.assertEqual(node_ids, [node.id])

    def test_put_allows_to_overwrite_a_node(self):
        node = larch.LeafNode(0, [], [])
        self.ns.put_node(node)
        node = larch.LeafNode(0, ['foo'], ['bar'])
        self.ns.put_node(node)
        new = self.ns.get_node(0)
        self.assertEqual(new.keys(), ['foo'])
        self.assertEqual(new.values(), ['bar'])

    def test_put_allows_to_overwrite_a_node_after_upload_queue_push(self):
        node = larch.LeafNode(0, [], [])
        self.ns.put_node(node)
        self.ns.commit()
        node = larch.LeafNode(0, ['foo'], ['bar'])
        self.ns.put_node(node)
        self.ns.commit()
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

