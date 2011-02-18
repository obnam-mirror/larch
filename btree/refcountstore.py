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


import ConfigParser
import logging
import lru
import os
import StringIO
import struct
import tempfile

import btree


class RefcountStore(object):

    '''Store node reference counts.
    
    Each node has a reference count, which gets stored on disk.
    Reference counts are grouped into blocks of self.per_group counts,
    and each group is stored in its own file. This balances the
    per-file overhead with the overhead of keeping a lot of unneeded
    reference counts in memory.
    
    Only those blocks that are used get loaded into memory. Blocks
    that are full of zeroes are not stored in files, to save space.
    
    '''

    per_group = 2**15
    refcountdir = 'refcounts'

    def __init__(self, node_store):
        self.node_store = node_store
        self.refcounts = dict()
        self.dirty = set()

    def get_refcount(self, node_id):
        if node_id not in self.refcounts:
            group = self.load_refcount_group(self.start_id(node_id))
            if group is None:
                self.refcounts[node_id] = 0
            else:
                for x, count in group:
                    if x not in self.dirty:
                        self.refcounts[x] = count
        return self.refcounts[node_id]

    def set_refcount(self, node_id, refcount):
        if refcount == 0:
            if node_id in self.refcounts:
                del self.refcounts[node_id]
        else:
            self.refcounts[node_id] = refcount
        self.dirty.add(node_id)

    def save_refcounts(self):
        if self.dirty:
            level = logging.getLogger().getEffectiveLevel()
            dirname = os.path.join(self.node_store.dirname, self.refcountdir)
            if not self.node_store.vfs.exists(dirname):
                self.node_store.vfs.makedirs(dirname)
            ids = sorted(self.dirty)
            for start_id in range(self.start_id(ids[0]), 
                                  self.start_id(ids[-1]) + 1, 
                                  self.per_group):
                encoded = self.encode_refcounts(start_id, self.per_group)
                filename = self.group_filename(start_id)
                self.node_store.vfs.overwrite_file(filename, encoded)
            self.dirty.clear()

    def load_refcount_group(self, start_id):
        filename = self.group_filename(start_id)
        if self.node_store.vfs.exists(filename):
            encoded = self.node_store.vfs.cat(filename)
            return self.decode_refcounts(encoded)

    def group_filename(self, start_id):
        return os.path.join(self.node_store.dirname, self.refcountdir,
                            'refcounts-%d' % start_id)

    def start_id(self, node_id):
        return (node_id / self.per_group) * self.per_group

    def encode_refcounts(self, start_id, how_many):
        fmt = '!QH' + 'H' * how_many
        args = ([start_id, how_many] +
                [self.refcounts.get(i, 0)
                 for i in range(start_id, start_id + how_many)])
        return struct.pack(fmt, *args)

    def decode_refcounts(self, encoded):
        n = struct.calcsize('!QH')
        start_id, how_many = struct.unpack('!QH', encoded[:n])
        counts = struct.unpack('!' + 'H' * how_many, encoded[n:])
        return [(start_id + i, counts[i]) for i in range(how_many)]

