# Copyright 2012  Lars Wirzenius
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


class JournalTests(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.fs = larch.LocalFS()
        self.j = larch.Journal(self.fs, self.tempdir)
        
    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def join(self, *args):
        return os.path.join(self.tempdir, *args)

    def test_constructs_new_filename(self):
        self.assertEqual(self.j._new(self.join('foo')),
                         self.join('new', 'foo'))

    def test_constructs_deleted_filename(self):
        self.assertEqual(self.j._deleted(self.join('foo')),
                         self.join('delete', 'foo'))
        
    def test_has_no_pending_metadata_initially(self):
        self.assertFalse(self.j.metadata_is_pending())

    def test_does_not_know_random_directory_initially(self):
        self.assertFalse(self.j.exists(self.join('foo')))

    def test_creates_directory(self):
        dirname = self.join('foo')
        self.j.makedirs(dirname)
        self.assertTrue(self.j.exists(dirname))

    def test_rollback_undoes_new_directories(self):
        dirname = self.join('foo')
        self.j.makedirs(dirname)
        self.j.rollback()
        self.assertFalse(self.j.exists(dirname))

