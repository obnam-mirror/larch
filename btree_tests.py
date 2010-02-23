import unittest

import btree


class LeafNodeTests(unittest.TestCase):

    def setUp(self):
        self.key = 'key'
        self.value = 'value'
        self.leaf = btree.LeafNode(self.key, self.value)

    def test_has_key(self):
        self.assertEqual(self.leaf.key, self.key)

    def test_has_value(self):
        self.assertEqual(self.leaf.value, self.value)


class IndexNodeTests(unittest.TestCase):

    def setUp(self):
        self.leaf1 = btree.LeafNode('foo', 'foo')
        self.leaf2 = btree.LeafNode('bar', 'bar')
        self.node = btree.IndexNode(self.leaf1, self.leaf2)

    def test_has_first_child(self):
        self.assertEqual(self.node.child1, self.leaf1)
        
    def test_has_second_child(self):
        self.assertEqual(self.node.child2, self.leaf2)


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
                yield key
            else:
                for key in self.keys(node.child1):
                    yield key
                for key in self.keys(node.child2):
                    yield key

    def max_key(self, node):
        return max(self.keys(node))

    def min_key(self, node):
        return min(self.keys(node))

    def proper_search_tree(self, node):
        if node is None:
            return True
        if isinstance(node, btree.LeafNode):
            return True
        if not self.proper_search_tree(node.child1):
            return False
        if not self.proper_search_tree(node.child2):
            return False
        if self.child2 is None:
            return True
        return self.max_key(node.child1) < self.min_key(node.child2)

    def test_insert_many_respects_ordering_requirement(self):
        for i in range(100):
            key = str(i)
            value = key
            self.tree.insert(key, value)
            self.assert_(self.proper_search_tree(self.tree.root))

