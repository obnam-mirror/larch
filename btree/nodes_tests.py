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

    def test_returns_first_key(self):
        leaf = btree.LeafNode(0, [('foo', 'foo'), ('bar', 'bar')])
        self.assertEqual(leaf.first_key(), 'bar')

    def test_returns_pairs(self):
        self.assertEqual(self.leaf.pairs(), [('foo', 'bar')])

    def test_does_not_return_excluded_pairs(self):
        self.assertEqual(self.leaf.pairs(exclude=['foo']), [])


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

    def test_finds_child_containing_key(self):
        self.assertEqual(self.index.find_key_for_child_containing('barbar'),
                         'bar')

    def test_returns_none_when_no_child_contains_key(self):
        self.assertEqual(self.index.find_key_for_child_containing('a'), None)

