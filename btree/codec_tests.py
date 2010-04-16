import unittest

import btree


class NodeCodecTests(unittest.TestCase):

    def setUp(self):
        self.leaf = btree.LeafNode(1234, [('foo', 'bar')])
        self.index = btree.IndexNode(5678,
                                     [('bar', 1234), 
                                      ('foo', 7890)])
        self.codec = btree.NodeCodec(3)

    def test_leaf_round_trip_ok(self):
        encoded = self.codec.encode_leaf(self.leaf)
        self.assertEqual(self.codec.decode_leaf(encoded), self.leaf)

    def test_index_round_trip_ok(self):
        encoded = self.codec.encode_index(self.index)
        self.assertEqual(self.codec.decode_index(encoded), self.index)

