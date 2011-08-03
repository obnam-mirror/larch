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

import larch


class NodeCodecTests(unittest.TestCase):

    def setUp(self):
        self.leaf = larch.LeafNode(1234, ['foo', 'yoo'], ['bar', 'yoyo'])
        self.index = larch.IndexNode(5678, ['bar', 'foo'], [1234, 7890])
        self.codec = larch.NodeCodec(3)

    def test_has_format_version(self):
        self.assertNotEqual(self.codec.format, None)

    def test_returns_reasonable_size_for_empty_leaf(self):
        self.assert_(self.codec.leaf_size([], []) > 10)

    def test_returns_reasonable_size_for_empty_index(self):
        self.assert_(self.codec.index_size([], []) > 10)

    def test_returns_reasonable_size_for_empty_leaf_generic(self):
        leaf = larch.LeafNode(0, [], [])
        self.assert_(self.codec.size(leaf) > 10)
        
    def test_returns_ok_delta_for_added_key_value(self):
        leaf = larch.LeafNode(0, [], [])
        old_size = self.codec.leaf_size(leaf.keys(), leaf.values())
        new_size = self.codec.leaf_size_delta_add(old_size, 'bar')
        self.assert_(new_size > old_size + len('foo') + len('bar'))

    def test_returns_ok_delta_for_changed_value_of_same_size(self):
        leaf = larch.LeafNode(0, ['foo'], ['bar'])
        old_size = self.codec.leaf_size(leaf.keys(), leaf.values())
        new_size = self.codec.leaf_size_delta_replace(old_size, 'bar', 'xxx')
        self.assertEqual(new_size, old_size)

    def test_returns_ok_delta_for_changed_value_of_larger_size(self):
        leaf = larch.LeafNode(0, ['foo'], ['bar'])
        old_size = self.codec.leaf_size(leaf.keys(), leaf.values())
        new_size = self.codec.leaf_size_delta_replace(old_size, 'bar',
                                                      'foobar')
        self.assertEqual(new_size, old_size + len('foobar') - len('foo'))

    def test_returns_ok_delta_for_changed_value_of_shorter_size(self):
        leaf = larch.LeafNode(0, ['foo'], ['bar'])
        old_size = self.codec.leaf_size(leaf.keys(), leaf.values())
        new_size = self.codec.leaf_size_delta_replace(old_size, 'bar',  '')
        self.assertEqual(new_size, old_size - len('foo'))

    def test_returns_reasonable_size_for_empty_index_generic(self):
        index = larch.IndexNode(0, [], [])
        self.assert_(self.codec.size(index) > 10)

    def test_leaf_round_trip_ok(self):
        encoded = self.codec.encode_leaf(self.leaf)
        decoded = self.codec.decode_leaf(encoded)
        self.assertEqual(decoded, self.leaf)

    def test_index_round_trip_ok(self):
        encoded = self.codec.encode_index(self.index)
        decoded = self.codec.decode_index(encoded)
        self.assertEqual(decoded.keys(), self.index.keys())
        self.assertEqual(decoded.values(), self.index.values())
        self.assertEqual(decoded, self.index)

    def test_generic_round_trip_ok_for_leaf(self):
        encoded = self.codec.encode(self.leaf)
        self.assertEqual(self.codec.decode(encoded), self.leaf)

    def test_generic_round_trip_ok_for_index(self):
        encoded = self.codec.encode(self.index)
        self.assertEqual(self.codec.decode(encoded), self.index)

    def test_decode_leaf_raises_error_for_garbage(self):
        self.assertRaises(larch.CodecError, self.codec.decode_leaf, 'x'*1000)

    def test_decode_index_raises_error_for_garbage(self):
        self.assertRaises(larch.CodecError, self.codec.decode_index, 'x'*1000)

    def test_decode_raises_error_for_garbage(self):
        self.assertRaises(larch.CodecError, self.codec.decode, 'x'*1000)
    
    def test_returns_resonable_max_number_of_index_pairs(self):
        # Header is 16 bytes. A pair is key_bytes + 8 = 11.
        self.assert_(self.codec.max_index_pairs(32), 1)
        self.assert_(self.codec.max_index_pairs(64), 4)
