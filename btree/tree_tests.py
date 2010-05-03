import random
import sys
import unittest

import btree


class DummyNodeStore(object):

    def __init__(self, node_size, codec):
        self.node_size = node_size
        self.codec = codec
        self.nodes = dict()
        self.metadata = dict()

    def max_index_pairs(self):
        return 4

    def get_metadata_keys(self):
        return self.metadata.keys()

    def get_metadata(self, key):
        return self.metadata[key]
        
    def set_metadata(self, key, value):
        self.metadata[key] = value

    def save_metadata(self):
        pass
    
    def put_node(self, node_id, encoded):
        self.nodes[node_id] = encoded
        
    def get_node(self, node_id):
        return self.nodes[node_id]
        
    def find_nodes(self):
        return self.nodes.keys()


class KeySizeMismatchTests(unittest.TestCase):

    def setUp(self):
        self.err = btree.KeySizeMismatch('foo', 4)
        
    def test_error_message_contains_key(self):
        self.assert_('foo' in str(self.err))
        
    def test_error_message_contains_wanted_size(self):
        self.assert_('4' in str(self.err))


class BTreeTests(unittest.TestCase):

    def setUp(self):
        # We use a small node size so that all code paths are traversed
        # during testing. Use coverage.py to make sure they do.
        self.codec = btree.NodeCodec(3)
        self.ns = DummyNodeStore(64, self.codec)
        self.tree = btree.BTree(self.ns, 0)
        self.dump = False

    def test_new_node_ids_grow(self):
        id1 = self.tree.new_id()
        id2 = self.tree.new_id()
        self.assertEqual(id1 + 1, id2)

    def test_creates_leaf(self):
        leaf = self.tree.new_leaf([])
        self.assertEqual(leaf, self.tree.get_node(leaf.id))

    def test_creates_index(self):
        index = self.tree.new_index([])
        self.assertEqual(index, self.tree.get_node(index.id))

    def test_new_root_does_not_return_it(self):
        self.assertEqual(self.tree.new_root([]), None)

    def test_creates_root_with_id_zero(self):
        self.tree.new_root([])
        self.assertEqual(self.tree.root.id, 0)

    def test_is_empty(self):
        self.assertEqual(self.tree.root.keys(), [])
        
    def test_lookup_for_missing_key_raises_error(self):
        self.assertRaises(KeyError, self.tree.lookup, 'foo')

    def test_lookup_with_wrong_size_key_raises_error(self):
        self.assertRaises(btree.KeySizeMismatch, self.tree.lookup, '')

    def test_insert_inserts_key(self):
        self.tree.insert('foo', 'bar')
        self.assertEqual(self.tree.lookup('foo'), 'bar')

    def test_insert_replaces_value_for_existing_key(self):
        self.tree.insert('foo', 'foo')
        self.tree.insert('foo', 'bar')
        self.assertEqual(self.tree.lookup('foo'), 'bar')

    def test_insert_with_wrong_size_key_raises_error(self):
        self.assertRaises(btree.KeySizeMismatch, self.tree.insert, '', '')

    def test_remove_from_empty_tree_raises_keyerror(self):
        self.assertRaises(KeyError, self.tree.remove, 'foo')

    def test_remove_of_missing_key_raises_keyerror(self):
        self.tree.insert('bar', 'bar')
        self.assertRaises(KeyError, self.tree.remove, 'foo')

    def test_remove_removes_key(self):
        self.tree.insert('foo', 'bar')
        self.tree.remove('foo')
        self.assertRaises(KeyError, self.tree.lookup, 'foo')

    def test_remove_with_wrong_size_key_raises_error(self):
        self.assertRaises(btree.KeySizeMismatch, self.tree.remove, '')

    def keys_are_in_range(self, node, lower, upper, level=0):
        indent = 2
        if isinstance(node, btree.LeafNode):
            if self.dump:
                print '%*sleaf keys %s' % (level*indent, '', node.keys())
            for key in node.keys():
                if key < lower or key >= upper:
                    return False
        else:
            keys = node.keys()
            if self.dump: print '%*sin range; index keys = %s' % (level*indent, '', keys), 'lower..upper:', lower, upper
            if keys != sorted(keys):
                return False
            for i, key in enumerate(keys):
                if key < lower or key >= upper:
                    return False
                if i+1 == len(keys):
                    up = upper
                else:
                    up = keys[i+1]
                if self.dump: print '%*sin child, keys should be in %s..%s' % (level*indent, '', key, up)
                if not self.keys_are_in_range(self.tree.get_node(node[key]), key, up, level+1):
                    return False
        return True

    def find_largest_key(self, node):
        if isinstance(node, btree.LeafNode):
            return max(node.keys())
        else:
            return max(node.keys() + 
                       [self.find_largest_key(self.tree.get_node(node[key]))
                        for key in node.keys()])

    def nextkey(self, key):
        assert type(key) == str
        if key == '':
            return '\0'
        if key[-1] == '\xff':
            return key + '\0'
        else:
            return key[:-1] + chr(ord(key[-1]) + 1)

    def proper_search_tree(self, node):
        if not node.keys():
            return True
        minkey = node.keys()[0]
        maxkey = self.find_largest_key(node)
        if self.dump: print; print 'proper tree', minkey, self.nextkey(maxkey)
        return self.keys_are_in_range(node, minkey, self.nextkey(maxkey))

    def test_insert_many_respects_ordering_requirement(self):
        ints = range(100)
        random.shuffle(ints)
        for i in ints:
            key = '%03d' % i
            value = key
            self.tree.insert(key, value)
            self.assertEqual(self.tree.lookup(key), value)
            self.assert_(self.proper_search_tree(self.tree.root),
                         'key#%d failed' % (1 + ints.index(i)))

    def test_remove_many_works(self):
        ints = range(100)
        random.shuffle(ints)
        for i in ints:
            key = '%03d' % i
            value = key
            self.tree.insert(key, value)
            self.assertEqual(self.tree.lookup(key), value)
            self.tree.remove(key)
            self.assertRaises(KeyError, self.tree.lookup, key)
            self.assert_(self.proper_search_tree(self.tree.root),
                         msg='insert of %d in %s failed to keep tree ok' %
                         (i, ints))

    def dump_tree(self, node, f=sys.stdout, level=0):
        if not self.dump:
            return
        indent = 4
        if isinstance(node, btree.LeafNode):
            f.write('%*sLeaf:' % (level*indent, ''))
            for key in node.keys():
                f.write(' %s=%s' % (key, node[key]))
            f.write('\n')
        else:
            assert isinstance(node, btree.IndexNode)
            f.write('%*sIndex:\n' % (level*indent, ''))
            for key in node.keys():
                f.write('%*s%s:\n' % ((level+1)*indent, '', key))
                self.dump_tree(self.tree.get_node(node[key]), level=level+2)

    def test_insert_many_remove_many_works(self):
        keys = ['%03d' % i for i in range(100)]
        random.shuffle(keys)
        for key in keys:
            self.tree.insert(key, key)
            self.assert_(self.proper_search_tree(self.tree.root))
        if self.dump:
            print
            print
            self.dump_tree(self.tree.root)
            print
        for key in keys:
            if self.dump:
                print
                print 'removing', key
                self.dump_tree(self.tree.root)
            try:
                self.tree.remove(key)
            except:
                self.dump = True
                self.dump_tree(self.tree.root)
                ret = self.proper_search_tree(self.tree.root)
                print 'is it?', ret
                raise
            self.assert_(self.proper_search_tree(self.tree.root))
            if self.dump:
                print
                print
        self.assertEqual(self.tree.root.keys(), [])
        
    def test_persists(self):
        self.tree.insert('foo', 'bar')
        tree2 = btree.BTree(self.ns, 0)
        self.assertEqual(tree2.lookup('foo'), 'bar')

    def test_last_node_id_persists(self):
        node1 = self.tree.new_leaf([])
        tree2 = btree.BTree(self.ns, 0)
        node2 = tree2.new_leaf([])
        self.assertEqual(node1.id + 1, node2.id)


class BTreeBalanceTests(unittest.TestCase):

    def setUp(self):
        ns = DummyNodeStore(4096, btree.NodeCodec(2))
        self.tree = btree.BTree(ns, 0)
        self.keys = ['%02d' % i for i in range(10)]
        self.depth = None

    def leaves_at_same_depth(self, node, depth=0):
        if isinstance(node, btree.LeafNode):
            if self.depth is None:
                self.depth = depth
            return self.depth == depth
        else:
            assert isinstance(node, btree.IndexNode)
            for key in node:
                child = self.tree.get_node(node[key])
                if not self.leaves_at_same_depth(child, depth + 1):
                    return False
            return True
            
    def indexes_filled_right_amount(self, node, isroot=True):
        if isinstance(node, btree.IndexNode):
            if not isroot:
                if len(node) < self.fanout or len(node) > 2 * self.fanout + 1:
                    return False
            for key in node:
                child = self.tree.get_node(node[key])
                ok = self.indexes_filled_right_amount(child, isroot=False)
                if not ok:
                    return False
        return True

    def test_insert_puts_every_leaf_at_same_depth(self):
        self.assert_(self.leaves_at_same_depth(self.tree.root))
        for key in self.keys:
            self.tree.insert(key, key)
            self.depth = None
            self.assert_(self.leaves_at_same_depth(self.tree.root),
                         'key#%d failed' % (self.keys.index(key) + 1))
        
    def test_insert_fills_every_index_node_the_right_amount(self):
        self.assert_(self.indexes_filled_right_amount(self.tree.root))
        for key in self.keys:
            self.tree.insert(key, key)
            self.assert_(self.indexes_filled_right_amount(self.tree.root))
            
    def test_remove_keeps_every_leaf_at_same_depth(self):
        for key in self.keys:
            self.tree.insert(key, key)
        for key in self.keys:
            self.tree.remove(key)
            self.assert_(self.leaves_at_same_depth(self.tree.root))

