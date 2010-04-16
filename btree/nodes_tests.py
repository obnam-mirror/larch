import unittest

import btree


class LeafNodeTests(unittest.TestCase):

    def setUp(self):
        self.node_id = 12765
        self.leaf = btree.LeafNode(self.node_id, [('foo', 'bar')])

    def test_has_id(self):
        self.assertEqual(self.leaf.id, self.node_id)
        
    def test_has_keys(self):
        self.assertEqual(self.leaf.keys(), ['foo'])
        
    def test_has_value(self):
        self.assertEqual(self.leaf['foo'], 'bar')

    def test_sorts_keys(self):
        leaf = btree.LeafNode(0, [('foo', 'foo'), ('bar', 'bar')])
        self.assertEqual(leaf.keys(), sorted(['foo', 'bar']))


class IndexNodeTests(unittest.TestCase):

    def setUp(self):
        self.leaf1 = btree.LeafNode(0, [('bar', 'bar')])
        self.leaf2 = btree.LeafNode(1, [('foo', 'foo')])
        self.index_id = 1234
        self.index = btree.IndexNode(self.index_id,
                                     [('bar', self.leaf1.id), 
                                      ('foo', self.leaf2.id)])

    def test_has_id(self):
        self.assertEqual(self.index.id, self.index_id)
        
    def test_has_keys(self):
        self.assertEqual(self.index.keys(), ['bar', 'foo'])
        
    def test_has_children(self):
        self.assertEqual(sorted(self.index.values()), 
                         sorted([self.leaf1.id, self.leaf2.id]))

    def test_has_indexed_children(self):
        self.assertEqual(self.index['bar'], self.leaf1.id)
        self.assertEqual(self.index['foo'], self.leaf2.id)

