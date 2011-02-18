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


class NodeStoreDiskTests(unittest.TestCase, btree.NodeStoreTests):

    def setUp(self):
        self.node_size = 4096
        self.codec = btree.NodeCodec(self.key_bytes)
        self.tempdir = tempfile.mkdtemp()
        self.ns = self.new_ns()

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def new_ns(self):
        return nodestore_disk.NodeStoreDisk(self.tempdir, self.node_size,
                                            self.codec)

    def test_has_persistent_metadata(self):
        self.ns.set_metadata('foo', 'bar')
        self.ns.save_metadata()
        ns2 = self.new_ns()
        self.assertEqual(ns2.get_metadata('foo'), 'bar')

    def test_metadata_does_not_persist_without_saving(self):
        self.ns.set_metadata('foo', 'bar')
        ns2 = self.new_ns()
        self.assertEqual(ns2.get_metadata_keys(), [])

    def test_refcounts_persist(self):
        self.ns.set_refcount(0, 1234)
        self.per_group = 2
        self.ns.save_refcounts()
        ns2 = self.new_ns()
        self.assertEqual(self.ns.get_refcount(0), 1234)
        self.assertEqual(ns2.get_refcount(0), 1234)

    def test_put_refuses_too_large_a_node(self):
        node = btree.LeafNode(0, ['000'], ['x' * (self.node_size + 1)])
        def helper(node):
            self.ns.put_node(node)
            self.ns.push_upload_queue()
        self.assertRaises(btree.NodeTooBig, helper, node)
        
    def test_puts_and_gets_same_with_cache_emptied(self):
        node = btree.LeafNode(0, [], [])
        self.ns.put_node(node)
        self.ns.cache = lru.LRUCache(100)
        self.assertEqualNodes(self.ns.get_node(0), node)

    def test_put_uploads_queue_overflow(self):
        self.ns.upload_max = 2
        self.ns.upload_queue.max = self.ns.upload_max
        ids = range(self.ns.upload_max + 1)
        for i in ids:
            node = btree.LeafNode(i, [], [])
            self.ns.put_node(node)
        self.assertEqual(sorted(self.ns.list_nodes()), ids)
        for node_id in ids:
            self.ns.cache.remove(node_id)
            self.assertEqual(self.ns.get_node(node_id).id, node_id)
            
    def test_gets_node_from_disk(self):
        node = btree.LeafNode(0, [], [])
        self.ns.put_node(node)
        self.ns.push_upload_queue()
        ns2 = self.new_ns()
        node2 = ns2.get_node(node.id)
        self.assertEqual(node.id, node2.id)
        self.assertEqual(node.keys(), node2.keys())
        self.assertEqual(node.values(), node2.values())

