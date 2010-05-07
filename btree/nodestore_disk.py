import ConfigParser
import os
import struct

import btree


class RefcountStore(object):

    '''Store node reference counts.'''

    per_group = 2

    def __init__(self, dirname):
        self.dirname = dirname
        self.refcounts = dict()
        self.dirty = set()

    def get_refcount(self, node_id):
        if node_id in self.refcounts:
            return self.refcounts[node_id]
        else:
            group = self.load_refcount_group(self.group(node_id))
            for x in group:
                if x not in self.dirty:
                    self.refcounts[x] = group[x]
            return self.refcounts[node_id]

    def set_refcount(self, node_id, refcount):
        self.refcounts[node_id] = refcount
        self.dirty.add(node_id)

    def save_refcounts(self):
        ids = sorted(self.dirty)
        for start_id in range(self.group(ids[0]), self.group(ids[-1]) + 1, 
                              self.per_group):
            encoded = self.encode_refcounts(start_id, self.per_group)
            filename = self.group_filename(start_id)
            file(filename, 'w').write(encoded)
        self.dirty.clear()

    def load_refcount_group(self, start_id):
        filename = self.group_filename(start_id)
        if os.path.exists(filename):
            encoded = file(filename).read()
            return dict(self.decode_refcounts(encoded))
        else:
            return dict((x, 0) 
                        for x in range(start_id, start_id + self.per_group))

    def group_filename(self, start_id):
        return os.path.join(self.dirname, 'refcounts-%d' % start_id)

    def group(self, node_id):
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


class NodeStoreDisk(btree.NodeStore):

    '''An implementation of btree.NodeStore API for on-disk storage.
    
    The caller will specify a directory in which the nodes will be stored.
    Each node is stored in its own file, named after the node identifier.
    
    '''

    refcounts_per_group = 2**15

    def __init__(self, dirname, node_size, codec):
        btree.NodeStore.__init__(self, node_size, codec)
        self.dirname = dirname
        self.metadata_name = os.path.join(dirname, 'metadata')
        self.metadata = None
        self.rs = RefcountStore(self.dirname)

    def _load_metadata(self):
        if self.metadata is None:
            self.metadata = ConfigParser.ConfigParser()
            self.metadata.add_section('metadata')
            if os.path.exists(self.metadata_name):
                f = file(self.metadata_name)
                self.metadata.readfp(f)
                f.close()

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

    def remove_metadata(self, key):
        self._load_metadata()
        if self.metadata.has_option('metadata', key):
            self.metadata.remove_option('metadata', key)
        else:
            raise KeyError(key)

    def save_metadata(self):
        self._load_metadata()
        f = file(self.metadata_name + '_new', 'w')
        self.metadata.write(f)
        f.close()
        os.rename(self.metadata_name + '_new', self.metadata_name)

    def pathname(self, node_id):
        return os.path.join(self.dirname, '%d.node' % node_id)
        
    def put_node(self, node):
        encoded_node = self.codec.encode(node)
        if len(encoded_node) > self.node_size:
            raise btree.NodeTooBig(node.id, len(encoded_node))
        name = self.pathname(node.id)
        if os.path.exists(name):
            raise btree.NodeExists(node.id)
        file(name, 'w').write(encoded_node)
        
    def get_node(self, node_id):
        name = self.pathname(node_id)
        if os.path.exists(name):
            encoded = file(name).read()
            return self.codec.decode(encoded)
        else:
            raise btree.NodeMissing(node_id)
    
    def remove_node(self, node_id):
        name = self.pathname(node_id)
        if os.path.exists(name):
            os.remove(name)
        else:
            raise btree.NodeMissing(node_id)
        
    def list_nodes(self):
        return [int(x[:-len('.node')])
                for x in os.listdir(self.dirname)
                if x.endswith('.node')]

    def get_refcount(self, node_id):
        return self.rs.get_refcount(node_id)

    def set_refcount(self, node_id, refcount):
        self.rs.set_refcount(node_id, refcount)

    def save_refcounts(self):
        self.rs.save_refcounts()
