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

import larch
import nodestore_disk


class DummyNodeStore(object):

    def __init__(self, dirname):
        self.dirname = dirname
        self.vfs = self

    def makedirs(self, dirname):
        if not os.path.exists(dirname):
            os.makedirs(dirname)

    def cat(self, filename):
        return file(filename).read()

    def overwrite_file(self, filename, contents):
        file(filename, 'w').write(contents)

    def exists(self, filename):
        return os.path.exists(filename)

    def rename(self, old, new):
        os.rename(old, new)

    def remove(self, filename):
        os.remove(filename)


class RefcountStoreTests(unittest.TestCase):

    def setUp(self):
        self.dirname = tempfile.mkdtemp()
        self.rs = self.new_rs()

    def tearDown(self):
        shutil.rmtree(self.dirname)

    def new_rs(self):
        return larch.RefcountStore(DummyNodeStore(self.dirname))

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
        self.assertEqual(self.rs.start_id(0), 0)

    def test_group_returns_correct_start_id_for_last_id_in_group(self):
        self.assertEqual(self.rs.start_id(self.rs.per_group - 1), 0)

    def test_group_returns_correct_start_id_for_first_in_second_group(self):
        self.assertEqual(self.rs.start_id(self.rs.per_group),
                         self.rs.per_group)

    def test_group_returns_correct_start_id_for_second_in_second_group(self):
        self.assertEqual(self.rs.start_id(self.rs.per_group + 1),
                         self.rs.per_group)

