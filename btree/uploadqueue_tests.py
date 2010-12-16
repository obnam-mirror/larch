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


import lru
import os
import shutil
import tempfile
import unittest

import btree
import nodestore_disk


class UploadQueueTests(unittest.TestCase):

    def setUp(self):
        self.max_queue = 4
        self.nodes = []
        self.uq = btree.UploadQueue(self.really_put, self.max_queue)
        self.node = btree.LeafNode(1, [])

    def really_put(self, node):
        self.nodes.append(node)

    def test_sets_max_correctly(self):
        self.assertEqual(self.uq.max, self.max_queue)
        
    def test_has_no_nodes_initially(self):
        self.assertEqual(self.uq.list_ids(), [])
        
    def test_get_returns_None_for_nonexistent_node(self):
        self.assertEqual(self.uq.get(self.node.id), None)
        
    def test_puts_node(self):
        self.uq.put(self.node)
        self.assertEqual(self.uq.list_ids(), [self.node.id])
        self.assertEqual(self.uq.get(self.node.id), self.node)
        
    def test_put_replaces_existing_node(self):
        node2 = btree.LeafNode(1, [('foo', 'bar')])
        self.uq.put(self.node)
        self.uq.put(node2)
        self.assertEqual(self.uq.get(self.node.id), node2)
