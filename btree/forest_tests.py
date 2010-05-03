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


class ForestTests(unittest.TestCase):

    def setUp(self):
        self.codec = btree.NodeCodec(3)
        self.ns = btree.NodeStoreMemory(64, self.codec)
        self.forest = btree.Forest(self.ns)

    def test_has_no_trees_initially(self):
        self.assertEqual(self.forest.trees, [])

    def test_creates_a_tree(self):
        t = self.forest.new_tree()
        self.assert_(isinstance(t, btree.BTree))
        self.assertEqual(self.forest.trees, [t])

