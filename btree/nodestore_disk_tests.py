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


import shutil
import tempfile
import unittest

import btree
import nodestore_disk


class RefcountStoreTests(unittest.TestCase):

    def setUp(self):
        self.dirname = tempfile.mkdtemp()
        self.rs = self.new_rs()

    def tearDown(self):
        shutil.rmtree(self.dirname)

    def new_rs(self):
        return nodestore_disk.RefcountStore(self.dirname)

    def test_returns_zero_for_unset_refcount(self):
        self.assertEqual(self.rs.get_refcount(123), 0)

    def test_sets_refcount(self):
        self.rs.set_refcount(123, 1)
        self.assertEqual(self.rs.get_refcount(123), 1)

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
        ids = [0]
        self.per_group = 2
        self.ns.save_refcounts()
        ns2 = self.new_ns()
        self.assertEqual(self.ns.get_refcount(0), 1234)
        self.assertEqual(ns2.get_refcount(0), 1234)

    def test_put_refuses_too_large_a_node(self):
        node = btree.LeafNode(0, [('000', 'x' * (self.node_size + 1))])
        self.assertRaises(btree.NodeTooBig, self.ns.put_node, node)

