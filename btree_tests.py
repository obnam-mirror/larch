import random
import unittest

import btree


class LeafNodeTests(unittest.TestCase):

    def setUp(self):
        self.leaf = btree.LeafNode('foo', 'bar')
        
    def test_has_key(self):
        self.assertEqual(self.leaf.key, 'foo')
        
    def test_has_value(self):
        self.assertEqual(self.leaf.value, 'bar')


class IndexNodeTests(unittest.TestCase):

    def setUp(self):
        self.leaf1 = btree.LeafNode('bar', 'bar')
        self.leaf2 = btree.LeafNode('foo', 'foo')
        self.index = btree.IndexNode('bar', self.leaf1, 'foo', self.leaf2)
        
    def test_has_key1(self):
        self.assertEqual(self.index.key1, 'bar')
        
    def test_has_child1(self):
        self.assertEqual(self.index.child1, self.leaf1)
        
    def test_has_key2(self):
        self.assertEqual(self.index.key2, 'foo')
        
    def test_has_child2(self):
        self.assertEqual(self.index.child2, self.leaf2)


class BinarySearchTreeTests(unittest.TestCase):

    def setUp(self):
        self.tree = btree.BinarySearchTree()

    def test_tree_is_empty(self):
        self.assertEqual(self.tree.root, None)
        
    def test_lookup_for_missing_key_raises_error(self):
        self.assertRaises(KeyError, self.tree.lookup, 'foo')
        
    def test_insert_inserts_key(self):
        self.tree.insert('foo', 'bar')
        self.assertEqual(self.tree.lookup('foo'), 'bar')

    def test_insert_replaces_value_for_existing_key(self):
        self.tree.insert('foo', 'foo')
        self.tree.insert('foo', 'bar')
        self.assertEqual(self.tree.lookup('foo'), 'bar')

    def test_remove_of_missing_key_raises_keyerror(self):
        self.assertRaises(KeyError, self.tree.remove, 'foo')

    def test_remove_removes_key(self):
        self.tree.insert('foo', 'bar')
        self.tree.remove('foo')
        self.assertRaises(KeyError, self.tree.lookup, 'foo')

    def proper_search_tree(self, node):
        if node is None:
            return True
        if node.child1 is not None:
            if node.child1.key > node.key:
                return False
        if node.child2 is not None:
            if node.child2.key < node.key:
                return False
        return True

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
            self.assert_(self.proper_search_tree(self.tree.root))

