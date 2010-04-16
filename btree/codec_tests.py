import unittest

import btree


class NodeCodecTests(unittest.TestCase):

    def setUp(self):
        self.leaf = btree.LeafNode(1234, [('foo', 'bar')])
        self.index = btree.IndexNode(5678,
                                     [('bar', 1234), 
                                      ('foo', 7890)])
        self.codec = btree.NodeCodec(3)

    def test_returns_size_of_header_for_empty_leaf(self):
        self.assertEqual(self.codec.leaf_size([]), self.codec.leaf_header_size)

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

