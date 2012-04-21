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
        self.j = larch.Journal(True, self.fs, self.tempdir)
        
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
        
    def test_does_not_know_random_directory_initially(self):
        self.assertFalse(self.j.exists(self.join('foo')))

    def test_creates_directory(self):
        dirname = self.join('foo/bar')
        self.j.makedirs(dirname)
        self.assertTrue(self.j.exists(dirname))

    def test_rollback_undoes_directory_creation(self):
        dirname = self.join('foo/bar')
        self.j.makedirs(dirname)
        self.j.rollback()
        self.assertFalse(self.j.exists(dirname))

    def test_rollback_keeps_committed_directory(self):
        dirname = self.join('foo/bar')
        self.j.makedirs(dirname)
        self.j.commit()
        self.j.rollback()
        self.assertTrue(self.j.exists(dirname))

    def test_rollback_works_without_changes(self):
        self.assertEqual(self.j.rollback(), None)

    def test_creates_new_file(self):
        filename = self.join('foo/bar')
        self.j.overwrite_file(filename, 'bar')
        self.assertEqual(self.j.cat(filename), 'bar')

    def test_rollback_undoes_new_file(self):
        filename = self.join('foo/bar')
        self.j.overwrite_file(filename, 'bar')
        self.j.rollback()
        self.assertFalse(self.j.exists(filename))

    def test_commits_new_file(self):
        filename = self.join('foo/bar')
        self.j.overwrite_file(filename, 'bar')
        self.j.commit()
        self.j.rollback()
        self.assertEqual(self.j.cat(filename), 'bar')

    def test_creates_new_file_after_commit(self):
        filename = self.join('foo/bar')
        self.j.overwrite_file(filename, 'bar')
        self.j.commit()
        self.j.overwrite_file(filename, 'yo')
        self.assertEqual(self.j.cat(filename), 'yo')

    def test_rollback_brings_back_old_file(self):
        filename = self.join('foo/bar')
        self.j.overwrite_file(filename, 'bar')
        self.j.commit()
        self.j.overwrite_file(filename, 'yo')
        self.j.rollback()
        self.assertEqual(self.j.cat(filename), 'bar')

    def test_removes_uncommitted_file(self):
        filename = self.join('foo/bar')
        self.j.overwrite_file(filename, 'bar')
        self.j.remove(filename)
        self.assertFalse(self.j.exists(filename))

    def test_rollback_undoes_removal_of_uncommitted_file(self):
        filename = self.join('foo/bar')
        self.j.overwrite_file(filename, 'bar')
        self.j.remove(filename)
        self.j.rollback()
        self.assertFalse(self.j.exists(filename))

    def test_commits_file_removal(self):
        filename = self.join('foo/bar')
        self.j.overwrite_file(filename, 'bar')
        self.j.remove(filename)
        self.j.commit()
        self.j.rollback()
        self.assertFalse(self.j.exists(filename))

    def test_removes_committed_file(self):
        filename = self.join('foo/bar')
        self.j.overwrite_file(filename, 'bar')
        self.j.commit()
        self.j.remove(filename)
        self.assertFalse(self.j.exists(filename))

    def test_removing_committed_file_twice_causes_oserror(self):
        filename = self.join('foo/bar')
        self.j.overwrite_file(filename, 'bar')
        self.j.commit()
        self.j.remove(filename)
        self.assertRaises(OSError, self.j.remove, filename)

    def test_rollback_brings_back_committed_file(self):
        filename = self.join('foo/bar')
        self.j.overwrite_file(filename, 'bar')
        self.j.commit()
        self.j.remove(filename)
        self.j.rollback()
        self.assertEqual(self.j.cat(filename), 'bar')

    def test_commits_removal_of_committed_file(self):
        filename = self.join('foo/bar')
        self.j.overwrite_file(filename, 'bar')
        self.j.commit()
        self.j.remove(filename)
        self.j.commit()
        self.j.rollback()
        self.assertFalse(self.j.exists(filename))

    def test_commits_metadata(self):
        metadata = self.join('metadata')
        self.j.overwrite_file(metadata, 'yuck')
        self.j.commit()
        self.assertEqual(self.fs.cat(self.join(metadata)), 'yuck')

    def test_unflagged_commit_means_new_instance_rollbacks(self):
        filename = self.join('foo/bar')
        self.j.overwrite_file(filename, 'bar')
        
        j2 = larch.Journal(self.fs, self.tempdir)
        self.assertFalse(j2.exists(filename))

    def test_partial_commit_finished_by_new_instance(self):
        filename = self.join('foo/bar')
        metadata = self.join('metadata')
        self.j.overwrite_file(filename, 'bar')
        self.j.overwrite_file(metadata, '')
        self.j.commit(skip=[filename])
        
        j2 = larch.Journal(self.fs, self.tempdir)
        self.assertTrue(j2.exists(filename))


class ReadOnlyJournalTests(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.fs = larch.LocalFS()
        self.rw = larch.Journal(True, self.fs, self.tempdir)
        self.ro = larch.Journal(False, self.fs, self.tempdir)
        
    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def join(self, *args):
        return os.path.join(self.tempdir, *args)

    def test_does_not_know_random_directory_initially(self):
        self.assertFalse(self.ro.exists(self.join('foo')))

    def test_creating_directory_raises_error(self):
        self.assertRaises(larch.ReadOnlyMode, self.ro.makedirs, 'foo')

    def test_calling_rollback_raises_error(self):
        self.assertRaises(larch.ReadOnlyMode, self.ro.rollback)

    def test_readonly_mode_does_not_check_for_directory_creation(self):
        dirname = self.rw.join('foo/bar')
        self.rw.makedirs(dirname)
        self.assertFalse(self.ro.exists(dirname))

    def test_write_file_raisees_error(self):
        self.assertRaises(larch.ReadOnlyMode, 
                          self.ro.overwrite_file, 'foo', 'bar')

    def test_readonly_mode_does_not_check_for_new_file(self):
        self.rw.ovewrite_file('foo', 'bar')
        self.assertFalse(self.ro.exists('foo'))

    def test_readonly_mode_does_not_check_for_modified_file(self):
        self.rw.ovewrite_file('foo', 'first')
        self.rw.commit()
        self.assertEqual(self.ro.cat('foo'), 'first')
        self.rw.ovewrite_file('foo', 'second')
        self.assertEqual(self.ro.cat('foo'), 'first')

    def test_readonly_mode_does_not_know_file_is_deleted_in_journal(self):
        filename = self.join('foo/bar')
        self.rw.overwrite_file(filename, 'bar')
        self.rw.commit()
        self.rw.remove(filename)
        self.assertEqual(self.ro.cat(filename), 'bar')

