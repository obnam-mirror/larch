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

