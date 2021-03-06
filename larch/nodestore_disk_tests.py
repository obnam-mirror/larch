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


import os
import shutil
import tempfile
import unittest

import larch
import nodestore_disk


class NodeStoreDiskTests(unittest.TestCase, larch.NodeStoreTests):

    def setUp(self):
        self.node_size = 4096
        self.codec = larch.NodeCodec(self.key_bytes)
        self.tempdir = tempfile.mkdtemp()
        self.ns = self.new_ns()

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def new_ns(self, format=None):
        return nodestore_disk.NodeStoreDisk(True, self.node_size, self.codec,
                                            dirname=self.tempdir,
                                            format=format)

    def test_metadata_has_format_version(self):
        self.assertEqual(self.ns.get_metadata('format'), 
                         self.ns.format_version)

    def test_metadata_format_version_is_persistent(self):
        self.ns.save_metadata()
        ns2 = self.new_ns()
        self.assertEqual(ns2.get_metadata('format'),
                         ns2.format_version)

    def test_refuses_to_open_if_format_version_is_old(self):
        old = self.new_ns(format=0)
        old.save_metadata()
        new = self.new_ns(format=1)
        self.assertRaises(larch.Error, new.get_metadata, 'format')

    def test_refuses_to_open_if_format_version_is_not_there(self):
        self.ns.remove_metadata('format')
        self.ns.save_metadata()
        ns2 = self.new_ns()
        self.assertRaises(larch.Error, ns2.get_metadata, 'format')

    def test_has_persistent_metadata(self):
        self.ns.set_metadata('foo', 'bar')
        self.ns.save_metadata()
        ns2 = self.new_ns()
        self.assertEqual(ns2.get_metadata('foo'), 'bar')

    def test_metadata_does_not_persist_without_saving(self):
        self.ns.set_metadata('foo', 'bar')
        ns2 = self.new_ns()
        self.assertEqual(ns2.get_metadata_keys(), ['format'])

    def test_refcounts_persist(self):
        self.ns.set_refcount(0, 1234)
        self.per_group = 2
        self.ns.save_refcounts()
        self.ns.journal.commit()
        ns2 = self.new_ns()
        self.assertEqual(self.ns.get_refcount(0), 1234)
        self.assertEqual(ns2.get_refcount(0), 1234)

    def test_put_refuses_too_large_a_node(self):
        node = larch.LeafNode(0, ['000'], ['x' * (self.node_size + 1)])
        def helper(node):
            self.ns.put_node(node)
            self.ns.commit()
        self.assertRaises(larch.NodeTooBig, helper, node)
        
    def test_puts_and_gets_same_with_cache_emptied(self):
        node = larch.LeafNode(0, [], [])
        self.ns.put_node(node)
        self.ns.cache = larch.LRUCache(100)
        self.assertEqualNodes(self.ns.get_node(0), node)

    def test_put_uploads_queue_overflow(self):
        self.ns.upload_max = 2
        self.ns.upload_queue.max = self.ns.upload_max
        ids = range(self.ns.upload_max + 1)
        for i in ids:
            node = larch.LeafNode(i, [], [])
            self.ns.put_node(node)
        self.assertEqual(sorted(self.ns.list_nodes()), ids)
        for node_id in ids:
            self.ns.cache.remove(node_id)
            self.assertEqual(self.ns.get_node(node_id).id, node_id)
            
    def test_gets_node_from_disk(self):
        node = larch.LeafNode(0, [], [])
        self.ns.put_node(node)
        self.ns.commit()
        ns2 = self.new_ns()
        node2 = ns2.get_node(node.id)
        self.assertEqual(node.id, node2.id)
        self.assertEqual(node.keys(), node2.keys())
        self.assertEqual(node.values(), node2.values())

