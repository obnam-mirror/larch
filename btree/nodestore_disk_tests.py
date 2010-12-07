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


class DummyNodeStore(object):

    def __init__(self, dirname):
        self.dirname = dirname

    def mkdir(self, dirname):
        if not os.path.exists(dirname):
            os.mkdir(dirname)

    def read_file(self, filename):
        return file(filename).read()

    def write_file(self, filename, contents):
        file(filename, 'w').write(contents)

    def file_exists(self, filename):
        return os.path.exists(filename)

    def rename_file(self, old, new):
        os.rename(old, new)

    def remove_file(self, filename):
        os.remove(filename)


class RefcountStoreTests(unittest.TestCase):

    def setUp(self):
        self.dirname = tempfile.mkdtemp()
        self.rs = self.new_rs()

    def tearDown(self):
        shutil.rmtree(self.dirname)

    def new_rs(self):
        return nodestore_disk.RefcountStore(DummyNodeStore(self.dirname))

    def test_returns_zero_for_unset_refcount(self):
        self.assertEqual(self.rs.get_refcount(123), 0)

    def test_sets_refcount(self):
        self.rs.set_refcount(123, 1)
        self.assertEqual(self.rs.get_refcount(123), 1)

    def test_does_not_set_refcount_if_zero(self):
        self.rs.set_refcount(123, 0)
        self.assertFalse(123 in self.rs.refcounts)
        self.assertEqual(self.rs.get_refcount(123), 0)

    def test_removes_refcount_that_drops_to_zero(self):
        self.rs.set_refcount(123, 1)
        self.rs.set_refcount(123, 0)
        self.assertFalse(123 in self.rs.refcounts)
        self.assertEqual(self.rs.get_refcount(123), 0)

    def test_updates_refcount(self):
        self.rs.set_refcount(123, 1)
        self.rs.set_refcount(123, 2)
        self.assertEqual(self.rs.get_refcount(123), 2)

    def test_refcounts_are_not_saved_automatically(self):
        self.rs.set_refcount(123, 1)
        rs2 = self.new_rs()
        self.assertEqual(rs2.get_refcount(123), 0)

    def test_saves_refcounts(self):
        self.rs.set_refcount(123, 1)
        self.rs.save_refcounts()
        rs2 = self.new_rs()
        self.assertEqual(rs2.get_refcount(123), 1)

    def test_save_refcounts_works_without_changes(self):
        self.assertEqual(self.rs.save_refcounts(), None)

    def test_refcount_group_encode_decode_round_trip_works(self):
        refs = range(2048)
        for ref in refs:
            self.rs.set_refcount(ref, ref)
        encoded = self.rs.encode_refcounts(0, 1024)
        decoded = self.rs.decode_refcounts(encoded)
        self.assertEqual(decoded, [(x, x) for x in refs[:1024]])

    def test_group_returns_correct_start_id_for_node_zero(self):
        self.assertEqual(self.rs.group(0), 0)

    def test_group_returns_correct_start_id_for_last_id_in_group(self):
        self.assertEqual(self.rs.group(self.rs.per_group - 1), 0)

    def test_group_returns_correct_start_id_for_first_in_second_group(self):
        self.assertEqual(self.rs.group(self.rs.per_group),
                         self.rs.per_group)

    def test_group_returns_correct_start_id_for_second_in_second_group(self):
        self.assertEqual(self.rs.group(self.rs.per_group + 1),
                         self.rs.per_group)


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
        node = btree.LeafNode(0, [('000', 'x' * (self.node_size + 1))])
        def helper(node):
            self.ns.put_node(node)
            self.ns.push_upload_queue()
        self.assertRaises(btree.NodeTooBig, helper, node)
        
    def test_puts_and_gets_same_with_cache_emptied(self):
        node = btree.LeafNode(0, [])
        self.ns.put_node(node)
        self.ns.cache = lru.LRUCache(100)
        self.assertEqualNodes(self.ns.get_node(0), node)

    def test_put_uploads_queue_overflow(self):
        self.ns.upload_max = 2
        self.ns.upload_queue.max = self.ns.upload_max
        ids = range(self.ns.upload_max + 1)
        for i in ids:
            node = btree.LeafNode(i, [])
            self.ns.put_node(node)
        self.assertEqual(sorted(self.ns.list_nodes()), ids)
        for node_id in ids:
            self.ns.cache.remove(node_id)
            self.assertEqual(self.ns.get_node(node_id).id, node_id)
