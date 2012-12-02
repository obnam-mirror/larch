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


import errno
import logging
import os
import tracing

import larch


class ReadOnlyMode(larch.Error): # pragma: no cover

    def __init__(self):
        self.msg = 'Larch B-tree is in read-only mode, no changes allowed'


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
    * ``delete/x`` is a deleted file, created there as a flag file
    
    Commit does this:
    
    * for every ``delete/x``, remove ``x``
    * for every ``new/x`` except ``new/metadata``, move to ``x``
    * move ``new/metadata`` to ``metadata``
    
    Rollback does this:
    
    * remove every ``new/x``
    * remove every ``delete/x``
    
    When a journalled node store is opened, if ``new/metadata`` exists,
    the commit happens. Otherwise a rollback happens. This guarantees
    that the on-disk state is consistent.
    
    We only provide enough of a filesystem interface as is needed by
    NodeStoreDisk. For example, we do not care about directory removal.
    
    The journal can be opened in read-only mode, in which case it ignores
    any changes in ``new`` and ``delete``, and does not try to rollback or
    commit at start.

    '''
    
    flag_basename = 'metadata'
    
    def __init__(self, allow_writes, fs, storedir):
        logging.debug('Initializing Journal for %s' % storedir)
        self.allow_writes = allow_writes
        self.fs = fs
        self.storedir = storedir
        if not self.storedir.endswith(os.sep):
            self.storedir += os.sep
        self.newdir = os.path.join(self.storedir, 'new/')
        self.deletedir = os.path.join(self.storedir, 'delete/')
        self.flag_file = os.path.join(self.storedir, self.flag_basename)
        self.new_flag = os.path.join(self.newdir, self.flag_basename)

        if self.allow_writes:
            if self.fs.exists(self.new_flag):
                logging.debug('Automatically committing remaining changes')
                self.commit()
            else:
                logging.debug('Automatically rolling back remaining changes')
                self.rollback()
            self.new_files = set()
            self.deleted_files = set()

    def _require_rw(self):
        '''Raise error if modifications are not allowed.'''
        if not self.allow_writes:
            raise ReadOnlyMode()

    def _relative(self, filename):
        '''Return the part of filename that is relative to storedir.'''
        assert filename.startswith(self.storedir)
        return filename[len(self.storedir):]

    def _new(self, filename):
        '''Return name for a new file whose final name is filename.'''
        return os.path.join(self.newdir, self._relative(filename))

    def _deleted(self, filename):
        '''Return name for temporary name for file to be deleted.'''
        return os.path.join(self.deletedir, self._relative(filename))

    def _realname(self, journaldir, filename):
        '''Return real name for a file in a journal temporary directory.'''
        assert filename.startswith(journaldir)
        return os.path.join(self.storedir, filename[len(journaldir):])
    
    def exists(self, filename):
        if self.allow_writes:
            new = self._new(filename)
            deleted = self._deleted(filename)
            if new in self.new_files:
                return True
            elif deleted in self.deleted_files:
                return False
        return self.fs.exists(filename)
        
    def makedirs(self, dirname):
        tracing.trace(dirname)
        self._require_rw()
        x = self._new(dirname)
        self.fs.makedirs(x)
        self.new_files.add(x)

    def overwrite_file(self, filename, contents):
        tracing.trace(filename)
        self._require_rw()
        new = self._new(filename)
        self.fs.overwrite_file(new, contents)
        self.new_files.add(new)

    def cat(self, filename):
        if self.allow_writes:
            new = self._new(filename)
            deleted = self._deleted(filename)
            if new in self.new_files:
                return self.fs.cat(new)
            elif deleted in self.deleted_files:
                raise OSError(
                    errno.ENOENT, os.strerror(errno.ENOENT), filename)
        return self.fs.cat(filename)
            
    def remove(self, filename):
        tracing.trace(filename)
        self._require_rw()

        new = self._new(filename)
        deleted = self._deleted(filename)
        
        if new in self.new_files:
            self.fs.remove(new)
            self.new_files.remove(new)
        elif deleted in self.deleted_files:
            raise OSError((errno.ENOENT, os.strerror(errno.ENOENT), filename))
        else:
            self.fs.overwrite_file(deleted, '')
            self.deleted_files.add(deleted)

    def list_files(self, dirname):
        '''List all files.
        
        Files only, no directories.
        
        '''

        assert not dirname.startswith(self.newdir)
        assert not dirname.startswith(self.deletedir)

        if self.allow_writes:
            if self.fs.exists(dirname):
                for x in self.climb(dirname, files_only=True):
                    if self.exists(x):
                        yield x
            new = self._new(dirname)
            if self.fs.exists(new):
                for x in self.climb(new, files_only=True):
                    yield self._realname(self.newdir, x)
        else:
            if self.fs.exists(dirname):
                for x in self.climb(dirname, files_only=True):
                    in_new = x.startswith(self.newdir)
                    in_deleted = x.startswith(self.deletedir)
                    if not in_new and not in_deleted:
                        yield x

    def climb(self, dirname, files_only=False):
        basenames = self.fs.listdir(dirname)
        filenames = []
        for basename in basenames:
            pathname = os.path.join(dirname, basename)
            if self.fs.isdir(pathname):
                for x in self.climb(pathname, files_only=files_only):
                    yield x
            else:
                filenames.append(pathname)
        for filename in filenames:
            yield filename
        if not files_only:
            yield dirname

    def _clear_directory(self, dirname):
        tracing.trace(dirname)
        for pathname in self.climb(dirname):
            if pathname != dirname:
                if self.fs.isdir(pathname):
                    self.fs.rmdir(pathname)
                else:
                    self.fs.remove(pathname)

    def _vivify(self, dirname, exclude):
        tracing.trace('dirname: %s' % dirname)
        tracing.trace('exclude: %s' % repr(exclude))
        all_excludes = [dirname] + exclude
        for pathname in self.climb(dirname):
            if pathname not in all_excludes:
                r = self._realname(dirname, pathname)
                parent = os.path.dirname(r)
                if self.fs.isdir(pathname):
                    if not self.fs.exists(r):
                        if not self.fs.exists(parent):
                            self.fs.makedirs(parent)
                        self.fs.rename(pathname, r)
                else:
                    if not self.fs.exists(parent):
                        self.fs.makedirs(parent)
                    self.fs.rename(pathname, r)

    def rollback(self):
        tracing.trace('%s start' % self.storedir)
        self._require_rw()

        if self.fs.exists(self.newdir):
            self._clear_directory(self.newdir)

        if self.fs.exists(self.deletedir):
            self._clear_directory(self.deletedir)

        self.new_files = set()
        self.deleted_files = set()

        tracing.trace('%s done' % self.storedir)

    def _really_delete(self, deletedir):
        tracing.trace(deletedir)
        for pathname in self.climb(deletedir, files_only=True):
            if pathname != deletedir:
                realname = self._realname(deletedir, pathname)
                try:
                    self.fs.remove(realname)
                except OSError, e: # pragma: no cover
                    if e.errno not in (errno.ENOENT, errno.EISDIR):
                        raise
                self.fs.remove(pathname)

    def commit(self, skip=[]):
        tracing.trace('%s start' % self.storedir)
        self._require_rw()

        if self.fs.exists(self.deletedir):
            self._really_delete(self.deletedir)

        if self.fs.exists(self.newdir):
            skip = [self._new(x) for x in skip]
            self._vivify(self.newdir, [self.new_flag] + skip)
        if not skip and self.fs.exists(self.new_flag):
            self.fs.rename(self.new_flag, self.flag_file)

        self.new_files = set()
        self.deleted_files = set()

        tracing.trace('%s done' % self.storedir)
