import unittest

import btree


class NodeCodecTests(unittest.TestCase):

    def setUp(self):
        self.leaf = btree.LeafNode(1234, [('foo', 'bar'), ('yoo', 'yoyo')])
        self.index = btree.IndexNode(5678,
                                     [('bar', 1234), 
                                      ('foo', 7890)])
        self.codec = btree.NodeCodec(3)

    def test_returns_reasonable_size_for_empty_leaf(self):
        self.assert_(self.codec.leaf_size([]) > 10)

    def test_returns_reasonable_size_for_empty_index(self):
        self.assert_(self.codec.index_size([]) > 10)

    def test_returns_reasonable_size_for_empty_leaf_generic(self):
        leaf = btree.LeafNode(0, [])
        self.assert_(self.codec.size(leaf) > 10)

    def test_returns_reasonable_size_for_empty_index_generic(self):
        index = btree.IndexNode(0, [])
        self.assert_(self.codec.size(index) > 10)

    def test_leaf_round_trip_ok(self):
        encoded = self.codec.encode_leaf(self.leaf)
        self.assertEqual(self.codec.decode_leaf(encoded), self.leaf)

    def test_index_round_trip_ok(self):
        encoded = self.codec.encode_index(self.index)
        self.assertEqual(self.codec.decode_index(encoded), self.index)

    def test_generic_round_trip_ok_for_leaf(self):
        encoded = self.codec.encode(self.leaf)
        self.assertEqual(self.codec.decode(encoded), self.leaf)

    def test_generic_round_trip_ok_for_index(self):
        encoded = self.codec.encode(self.index)
        self.assertEqual(self.codec.decode(encoded), self.index)

