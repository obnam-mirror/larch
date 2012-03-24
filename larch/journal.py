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


class Journal(object):

    '''A journal layer on top of a virtual filesystem.
    
    The journal solves the problem of updating on-disk data structures
    atomically. Changes are first written to a journal, and then moved
    from there to the real location. If the program or system crashes,
    the changes can be completed later on, or rolled back, depending
    on what's needed for consistency.
    
    The journal works as follows:
    
    * ``x`` is the real filename
    * ``new/x`` is a new or modified file
    * ``delete/x`` is a deleted file, moved there immediately
    
    Commit does this:
    
    * for every ``delete/x``, remove it
    * for every ``new/x`` except ``new/metadata``, move to ``x``
    * move ``new/metadata`` to ``metadata``
    
    Rollback does this:
    
    * remove every ``new/x``
    * move every ``delete/x`` to ``x``
    
    When a journalled node store is opened, if ``new/metadata`` exists,
    the commit happens. Otherwise a rollback happens. This guarantees
    that the on-disk state is consistent.
    
    '''
    
    def __init__(self, fs, storedir):
        self.fs = fs
        self.storedir = storedir
        if not self.storedir.endswith(os.sep):
            self.storedir += os.sep

    def _relative(self, filename):
        '''Return the part of filename that is relative to storedir.'''
        assert filename.startswith(self.storedir)
        return filename[len(self.storedir):]

    def _new(self, filename):
        '''Return name for a new file whose final name is filename.'''
        return os.path.join(self.storedir, 'new', self._relative(filename))

    def _deleted(self, filename):
        '''Return name for temporary name for file to be deleted.'''
        return os.path.join(self.storedir, 'delete', self._relative(filename))
    
    def metadata_is_pending(self):
        return False

    def exists(self, filename):
        return (self.fs.exists(filename) or 
                self.fs.exists(self._new(filename)))
        
    def makedirs(self, dirname):
        x = self._new(dirname)
        self.fs.makedirs(x)

    def rmdir(self, dirname):
        new = self._new(dirname)
        deleted = self._deleted(dirname)
        if self.fs.exists(new):
            self.fs.rmdir(new)
        elif not self.fs.exists(deleted) and self.fs.exists(dirname):
            target_parent = self._new(os.path.dirname(dirname))
            self.fs.makedirs(target_parent)
            self.fs.rename(dirname, target_parent)
        else:
            # Either it doesn't exist at all, or we've already deleted 
            # it once after the latest commit.
            raise OSError((errno.ENOENT, os.strerror(errno.ENOENT), dirname))

    def overwrite_file(self, filename, contents):
        self.fs.overwrite_file(self._new(filename), contents)

    def cat(self, filename):
        new = self._new(filename)
        if self.fs.exists(new):
            return self.fs.cat(new)
        else:
            return self.fs.cat(filename)

    def _climb(self, dirname):
        basenames = self.fs.listdir(dirname)
        filenames = []
        for basename in basenames:
            pathname = os.path.join(dirname, basename)
            if self.fs.isdir(pathname):
                for x in self._climb(pathname):
                    yield x
            else:
                filenames.append(pathname)
        for filename in filenames:
            yield filename
        yield dirname

    def _clear_directory(self, dirname):
        basenames = self.fs.listdir(dirname)
        for basename in basenames:
            pathname = os.path.join(dirname, basename)
            if self.fs.isdir(pathname):
                self._clear_directory(pathname)
                self.fs.rmdir(pathname)
            else:
                self.fs.remove(pathname)

    def rollback(self):
        new = os.path.join(self.storedir, 'new')
        if self.fs.exists(new):
            self._clear_directory(new)

    def commit(self):
        new = os.path.join(self.storedir, 'new')
        for pathname in self._climb(new):
            if pathname != new:
                r = self._relative(pathname)
                assert r.startswith('new/')
                r = r[len('new/'):]
                r = os.path.join(self.storedir, r)
                if self.fs.isdir(pathname):
                    self.fs.makedirs(r)
                else:
                    dirname = os.path.dirname(r)
                    if not self.fs.exists(dirname):
                        self.fs.makedirs(dirname)
                    self.fs.rename(pathname, r)

