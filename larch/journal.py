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
    
    We only provide enough of a filesystem interface as is needed by
    NodeStoreDisk. For example, we do not care about directory removal.
    
    '''
    
    flag_basename = 'metadata'
    
    def __init__(self, fs, storedir):
        logging.debug('Initializing Journal for %s' % storedir)
        self.fs = fs
        self.storedir = storedir
        if not self.storedir.endswith(os.sep):
            self.storedir += os.sep
        self.newdir = os.path.join(self.storedir, 'new/')
        self.deletedir = os.path.join(self.storedir, 'delete/')
        self.flag_file = os.path.join(self.storedir, self.flag_basename)
        self.new_flag = os.path.join(self.newdir, self.flag_basename)

        logging.debug('journal: new_flag = %s' % self.new_flag)        
        if self.fs.exists(self.new_flag):
            logging.debug('Automatically committing remaining changes')
            self.commit()
        else:
            logging.debug('Automatically rolling back remaining changes')
            self.rollback()

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
    
    def exists(self, filename):
        return (self.fs.exists(filename) or 
                self.fs.exists(self._new(filename)))
        
    def makedirs(self, dirname):
        x = self._new(dirname)
        self.fs.makedirs(x)

    def overwrite_file(self, filename, contents):
        self.fs.overwrite_file(self._new(filename), contents)

    def cat(self, filename):
        new = self._new(filename)
        if self.fs.exists(new):
            return self.fs.cat(new)
        else:
            return self.fs.cat(filename)
            
    def remove(self, filename):
        new = self._new(filename)
        deleted = self._deleted(filename)
        
        if self.fs.exists(new):
            self.fs.remove(new)
        elif self.fs.exists(deleted):
            raise OSError((errno.ENOENT, os.strerror(errno.ENOENT), filename))
        else:
            dirname = os.path.dirname(deleted)
            if not self.fs.exists(dirname):
                self.fs.makedirs(dirname)
            self.fs.rename(filename, deleted)

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
        for pathname in self._climb(dirname):
            if pathname != dirname:
                if self.fs.isdir(pathname):
                    self._clear_directory(pathname)
                    self.fs.rmdir(pathname)
                else:
                    self.fs.remove(pathname)

    def _vivify(self, dirname, exclude):
        all_excludes = [dirname] + exclude
        for pathname in self._climb(dirname):
            if pathname not in all_excludes:
                r = os.path.join(self.storedir, pathname[len(dirname):])
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

        if self.fs.exists(self.newdir):
            self._clear_directory(self.newdir)

        if self.fs.exists(self.deletedir):
            self._vivify(self.deletedir, [])

        tracing.trace('%s done' % self.storedir)

    def commit(self, skip=[]):
        tracing.trace('%s start' % self.storedir)

        if self.fs.exists(self.deletedir):
            self._clear_directory(self.deletedir)

        if self.fs.exists(self.newdir):
            skip = [self._new(x) for x in skip]
            self._vivify(self.newdir, [self.new_flag] + skip)
        if not skip and self.fs.exists(self.new_flag):
            self.fs.rename(self.new_flag, self.flag_file)

        tracing.trace('%s done' % self.storedir)
