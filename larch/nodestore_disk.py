# Copyright 2010, 2011  Lars Wirzenius
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# (at your option) any later version.
# the Free Software Foundation, either version 3 of the License, or
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
import os
import StringIO
import struct
import tempfile
import tracing

import larch


DIR_DEPTH = 3
DIR_BITS = 12
DIR_SKIP = 13


class FormatProblem(larch.Error): # pragma: no cover

    def __init__(self, msg):
        self.msg = msg


class LocalFS(object): # pragma: no cover

    '''Access to local filesystem.
    
    The ``NodeStoreDisk`` class will use a class with this interface
    to do disk operations. This class implements access to the local
    filesystem.
    
    '''

    def makedirs(self, dirname):
        '''Create directories, simliar to os.makedirs.'''
        if not os.path.exists(dirname):
            os.makedirs(dirname)
            
    def rmdir(self, dirname):
        '''Remove an empty directory.'''
        os.rmdir(dirname)

    def cat(self, filename):
        '''Return contents of a file.'''
        return file(filename).read()

    def overwrite_file(self, filename, contents):
        '''Write data to disk. File may exist already.'''
        dirname = os.path.dirname(filename)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        fd, tempname = tempfile.mkstemp(dir=dirname)
        os.write(fd, contents)
        os.close(fd)
        os.rename(tempname, filename)

    def exists(self, filename):
        '''Does a file exist already?'''
        return os.path.exists(filename)

    def isdir(self, filename):
        '''Does filename and is it a directory?'''
        return os.path.isdir(filename)

    def rename(self, old, new):
        '''Rename a file.'''
        os.rename(old, new)

    def remove(self, filename):
        '''Remove a file.'''
        os.remove(filename)
        
    def listdir(self, dirname):
        '''Return basenames from directory.'''
        return os.listdir(dirname)


class NodeStoreDisk(larch.NodeStore):

    '''An implementation of larch.NodeStore API for on-disk storage.
    
    The caller will specify a directory in which the nodes will be stored.
    Each node is stored in its own file, named after the node identifier.

    The ``vfs`` optional argument to the initializer can be used to
    override filesystem access. By default, the local filesystem is
    used, but any class can be substituted.
    
    '''
    
    # The on-disk format version is format_base combined with whatever
    # format the codec specifies.
    format_base = 1

    nodedir = 'nodes'

    def __init__(self, allow_writes, node_size, codec, dirname=None, 
                 upload_max=1024, lru_size=500, vfs=None, format=None):
        tracing.trace('new NodeStoreDisk: %s', dirname)
        assert dirname is not None
        if format is not None:
            tracing.trace('forcing format_base: %s', format)
            self.format_base = format
        larch.NodeStore.__init__(self, node_size, codec)
        self.dirname = dirname
        self.metadata_name = os.path.join(dirname, 'metadata')
        self.metadata = None
        self.rs = larch.RefcountStore(self)
        self.cache_size = lru_size
        self.cache = larch.LRUCache(self.cache_size)
        self.upload_max = upload_max
        self.upload_queue = larch.UploadQueue(self._really_put_node, 
                                              self.upload_max)
        self.vfs = vfs if vfs != None else LocalFS()
        self.journal = larch.Journal(allow_writes, self.vfs, dirname)
        self.idpath = larch.IdPath(os.path.join(dirname, self.nodedir), 
                                   DIR_DEPTH, DIR_BITS, DIR_SKIP)

    @property
    def format_version(self):
        return '%s/%s' % (self.format_base, self.codec.format)

    def _load_metadata(self):
        if self.metadata is None:
            tracing.trace('load metadata')
            self.metadata = ConfigParser.ConfigParser()
            self.metadata.add_section('metadata')
            if self.journal.exists(self.metadata_name):
                tracing.trace('metadata file (%s) exists, reading it' % 
                                self.metadata_name)
                data = self.journal.cat(self.metadata_name)
                f = StringIO.StringIO(data)
                self.metadata.readfp(f)
                self._verify_metadata()
            else:
                self.metadata.set('metadata', 'format', self.format_version)

    def _verify_metadata(self):
        if not self.metadata.has_option('metadata', 'format'):
            raise FormatProblem('larch on-disk format missing '
                                '(old version?): %s' % self.dirname)
        format = self.metadata.get('metadata', 'format')
        if format != self.format_version:
            raise FormatProblem('larch on-disk format is incompatible '
                                '(is %s, should be %s): %s' %
                                (format, self.format_version,
                                 self.dirname))

    def get_metadata_keys(self):
        self._load_metadata()
        return self.metadata.options('metadata')
        
    def get_metadata(self, key):
        self._load_metadata()
        if self.metadata.has_option('metadata', key):
            return self.metadata.get('metadata', key)
        else:
            raise KeyError(key)
        
    def set_metadata(self, key, value):
        self._load_metadata()
        self.metadata.set('metadata', key, value)
        tracing.trace('key=%s value=%s', repr(key), repr(value))

    def remove_metadata(self, key):
        self._load_metadata()
        if self.metadata.has_option('metadata', key):
            self.metadata.remove_option('metadata', key)
        else:
            raise KeyError(key)

    def save_metadata(self):
        tracing.trace('saving metadata')
        self._load_metadata()
        f = StringIO.StringIO()
        self.metadata.write(f)
        self.journal.overwrite_file(self.metadata_name, f.getvalue())

    def pathname(self, node_id):
        return self.idpath.convert(node_id)
        
    def put_node(self, node):
        tracing.trace('putting node %s into cache and upload queue' % node.id)
        node.frozen = True
        self.cache.add(node.id, node)
        self.upload_queue.put(node)

    def push_upload_queue(self):
        tracing.trace('pushing upload queue')
        self.upload_queue.push()
        self.cache.log_stats()
        self.cache = larch.LRUCache(self.cache_size)

    def _really_put_node(self, node):
        tracing.trace('really put node %s' % node.id)
        encoded_node = self.codec.encode(node)
        if len(encoded_node) > self.node_size:
            raise larch.NodeTooBig(node, len(encoded_node))
        name = self.pathname(node.id)
        tracing.trace('node %s to be stored in %s' % (node.id, name))
        self.journal.overwrite_file(name, encoded_node)
        
    def get_node(self, node_id):
        tracing.trace('getting node %s' % node_id)
        node = self.cache.get(node_id)
        if node is not None:
            tracing.trace('cache hit: %s' % node_id)
            return node

        node = self.upload_queue.get(node_id)
        if node is not None:
            tracing.trace('upload queue hit: %s' % node_id)
            return node

        name = self.pathname(node_id)
        tracing.trace('reading node %s from file %s' % (node_id, name))
        try:
            encoded = self.journal.cat(name)
        except (IOError, OSError), e:
            logging.error('Error reading node: %s: %s: %s' % 
                            (e.errno, e.strerror, e.filename or name))
            raise larch.NodeMissing(self.dirname, node_id)
        else:
            node = self.codec.decode(encoded)
            node.frozen = True
            self.cache.add(node.id, node)
            return node

    def start_modification(self, node):
        tracing.trace('start modiyfing node %s' % node.id)
        self.upload_queue.remove(node.id)
        node.frozen = False
    
    def remove_node(self, node_id):
        tracing.trace('removing node %s (incl. cache and upload queue)' % 
                        node_id)
        self.cache.remove(node_id)
        got_it = self.upload_queue.remove(node_id)
        name = self.pathname(node_id)
        if self.journal.exists(name):
            self.journal.remove(name)
        elif not got_it:
            raise larch.NodeMissing(self.dirname, node_id)
        
    def list_nodes(self):
        queued = self.upload_queue.list_ids()

        nodedir = os.path.join(self.dirname, self.nodedir)
        uploaded = []
        if self.journal.exists(nodedir):
            for filename in self.journal.list_files(nodedir):
                uploaded.append(int(os.path.basename(filename), 16))
        return queued + uploaded

    def get_refcount(self, node_id):
        return self.rs.get_refcount(node_id)

    def set_refcount(self, node_id, refcount):
        self.rs.set_refcount(node_id, refcount)

    def save_refcounts(self):
        tracing.trace('saving refcounts')
        self.rs.save_refcounts()
        
    def commit(self):
        self.push_upload_queue()
        self.save_metadata()
        self.journal.commit()

