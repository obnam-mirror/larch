# Copyright 2010  Lars Wirzenius
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


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

    def test_decode_leaf_raises_error_for_garbage(self):
        self.assertRaises(btree.CodecError, self.codec.decode_leaf, 'x'*1000)

    def test_decode_index_raises_error_for_garbage(self):
        self.assertRaises(btree.CodecError, self.codec.decode_index, 'x'*1000)

    def test_decode_raises_error_for_garbage(self):
        self.assertRaises(btree.CodecError, self.codec.decode, 'x'*1000)

