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

    def keys(self, node):
        if node is not None:
            if isinstance(node, btree.LeafNode):
                yield node.key
            else:
                for key in self.keys(node.child1):
                    yield key
                for key in self.keys(node.child2):
                    yield key

    def proper_search_tree(self, node):
        if node is None:
            return True
        if isinstance(node, btree.LeafNode):
            return True
            
        if node.key1 > min(self.keys(node.child1)):
            raise Exception('key1 bigger than child1')
            return False
        if node.key2 is not None:
            if node.key2 > min(self.keys(node.child2)):
                raise Exception('key2 bigger than child1')
                return False
            if node.key2 <= max(self.keys(node.child1)):
                raise Exception('key2 <= max(child1)')
                return False
            if node.key1 >= node.key2:
                raise Exception('key1 >= key2')
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
            self.assert_(self.proper_search_tree(self.tree.root),
                         msg='insert of %d in %s failed to keep tree ok' %
                         (i, ints))

