import random
import unittest

import btree


class LeafNodeTests(unittest.TestCase):

    def setUp(self):
        self.leaf = btree.LeafNode([('foo', 'bar')])
        
    def test_has_keys(self):
        self.assertEqual(self.leaf.keys(), ['foo'])
        
    def test_has_value(self):
        self.assertEqual(self.leaf['foo'], 'bar')

    def test_sorts_keys(self):
        leaf = btree.LeafNode([('foo', 'foo'), ('bar', 'bar')])
        self.assertEqual(leaf.keys(), sorted(['foo', 'bar']))


class IndexNodeTests(unittest.TestCase):

    def setUp(self):
        self.leaf1 = btree.LeafNode([('bar', 'bar')])
        self.leaf2 = btree.LeafNode([('foo', 'foo')])
        self.index = btree.IndexNode([('bar', self.leaf1), 
                                      ('foo', self.leaf2)])
        
    def test_has_keys(self):
        self.assertEqual(self.index.keys(), ['bar', 'foo'])
        
    def test_has_children(self):
        self.assertEqual(sorted(self.index.values()), 
                         sorted([self.leaf1, self.leaf2]))

    def test_has_indexed_children(self):
        self.assertEqual(self.index['bar'], self.leaf1)
        self.assertEqual(self.index['foo'], self.leaf2)
        

class BTreeTests(unittest.TestCase):

    def setUp(self):
        self.fanout = 2
        self.tree = btree.BTree(self.fanout)

    def test_has_fanout(self):
        self.assertEqual(self.tree.fanout, self.fanout)

    def test_is_empty(self):
        self.assertEqual(self.tree.root.keys(), [])
        
    def test_lookup_for_missing_key_raises_error(self):
        self.assertRaises(KeyError, self.tree.lookup, 'foo')

    def test_insert_inserts_key(self):
        self.tree.insert('foo', 'bar')
        self.assertEqual(self.tree.lookup('foo'), 'bar')

    def test_insert_replaces_value_for_existing_key(self):
        self.tree.insert('foo', 'foo')
        self.tree.insert('foo', 'bar')
        self.assertEqual(self.tree.lookup('foo'), 'bar')

    def test_remove_from_empty_tree_raises_keyerror(self):
        self.assertRaises(KeyError, self.tree.remove, 'foo')

    def test_remove_of_missing_key_raises_keyerror(self):
        self.tree.insert('bar', 'bar')
        self.assertRaises(KeyError, self.tree.remove, 'foo')

    def test_remove_removes_key(self):
        self.tree.insert('foo', 'bar')
        self.tree.remove('foo')
        self.assertRaises(KeyError, self.tree.lookup, 'foo')

    def keys_are_in_range(self, node, lower, upper):
        if isinstance(node, btree.LeafNode):
            for key in node.keys():
                if key < lower or key >= upper:
                    return False
        else:
            keys = node.keys()
            if keys != sorted(keys):
                return False
            for i, key in enumerate(keys):
                if key < lower or key >= upper:
                    return False
                if i+1 == len(keys):
                    up = upper
                else:
                    up = keys[i+1]
                if not self.keys_are_in_range(node[key], key, up):
                    return False
        return True

    def find_largest_key(self, node):
        if isinstance(node, btree.LeafNode):
            return max(node.keys())
        else:
            return max(node.keys() + 
                       [self.find_largest_key(node[key])
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
        return self.keys_are_in_range(node, minkey, self.nextkey(maxkey))

    def test_insert_many_respects_ordering_requirement(self):
        ints = range(100)
        random.shuffle(ints)
        for i in ints:
            key = str(i)
            value = key
            self.tree.insert(key, value)
            self.assertEqual(self.tree.lookup(key), value)
            self.assert_(self.proper_search_tree(self.tree.root))

    def test_remove_many_works(self):
        ints = range(100)
        random.shuffle(ints)
        for i in ints:
            key = str(i)
            value = key
            self.tree.insert(key, value)
            self.assertEqual(self.tree.lookup(key), value)
            self.tree.remove(key)
            self.assertRaises(KeyError, self.tree.lookup, key)
            self.assert_(self.proper_search_tree(self.tree.root),
                         msg='insert of %d in %s failed to keep tree ok' %
                         (i, ints))

    def test_insert_many_remove_many_works(self):
        keys = [str(i) for i in range(100)]
        random.shuffle(keys)
        tree = btree.BTree(self.fanout)
        for key in keys:
            tree.insert(key, key)
            self.assert_(self.proper_search_tree(self.tree.root))
        for key in keys:
            tree.remove(key)
            self.assert_(self.proper_search_tree(self.tree.root))


class BTreeBalanceTests(unittest.TestCase):

    def setUp(self):
        self.fanout = 2
        self.tree = btree.BTree(self.fanout)
        self.keys = [str(i) for i in range(100)]
        self.depth = None

    def leaves_at_same_depth(self, node, depth=0):
        if isinstance(node, btree.LeafNode):
            if self.depth is None:
                self.depth = depth
            return self.depth == depth
        else:
            for key in node:
                if not self.leaves_at_same_depth(node[key], depth + 1):
                    return False
            return True
            
    def indexes_filled_right_amount(self, node, isroot=True):
        if isinstance(node, btree.IndexNode):
            if not isroot:
                if len(node) < self.fanout or len(node) > 2 * self.fanout + 1:
                    return False
            for key in node:
                ok = self.indexes_filled_right_amount(node[key], isroot=False)
                if not ok:
                    return False
        return True
            
    def test_insert_puts_every_leaf_at_same_depth(self):
        for key in self.keys:
            self.tree.insert(key, key)
            self.assert_(self.leaves_at_same_depth(self.tree.root))
        
    def test_insert_fills_every_index_node_the_right_amount(self):
        for key in self.keys:
            self.tree.insert(key, key)
            self.assert_(self.indexes_filled_right_amount(self.tree.root))
            
    def test_remove_keeps_every_leaf_at_same_depth(self):
        for key in self.keys:
            self.tree.insert(key, key)
        for key in self.keys:
            self.tree.remove(key)
            self.assert_(self.leaves_at_same_depth(self.tree.root))
        
    def test_remove_keeps_every_index_node_the_right_amount(self):
        for key in self.keys:
            self.tree.insert(key, key)
        for key in self.keys:
            self.tree.remove(key)
            self.assert_(self.indexes_filled_right_amount(self.tree.root))

