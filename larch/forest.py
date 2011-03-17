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


import larch


class BadKeySize(Exception):

    def __init__(self, store_key_size, wanted_key_size):
        self.msg = ('Node store has key size %s, program wanted %s' %
                    (store_key_size, wanted_key_size))
    
    def __str__(self):
        return self.msg


class BadNodeSize(Exception):

    def __init__(self, store_node_size, wanted_node_size):
        self.msg = ('Node store has node size %s, program wanted %s' %
                    (store_node_size, wanted_node_size))
    
    def __str__(self):
        return self.msg


class Forest(object):

    '''A collection of BTrees in the same node store.'''

    def __init__(self, node_store):
        self.node_store = node_store
        self.trees = []
        self.last_id = 0
        self.read_metadata()

    def read_metadata(self):
        keys = self.node_store.get_metadata_keys()
        if 'last_id' in keys:
            self.last_id = int(self.node_store.get_metadata('last_id'))
        if 'root_ids' in keys:
            s = self.node_store.get_metadata('root_ids')
            if s.strip():
                root_ids = [int(x) for x in s.split(',')]
                self.trees = [larch.BTree(self, self.node_store, root_id)
                              for root_id in root_ids]
            else:
                self.trees = []
    
    def new_id(self):
        '''Generate next node id for this forest.'''
        self.last_id += 1
        return self.last_id

    def new_tree(self, old=None):
        '''Create a new tree.

        If old is None, a completely new tree is created. Otherwise,
        a clone of an existing one is created.

        '''

        if old:
            old_root = self.node_store.get_node(old.root.id)
            keys = old_root.keys()
            values = old_root.values()
        else:
            keys = []
            values = []
        t = larch.BTree(self, self.node_store, None)
        t.set_root(t.new_index(keys, values))
        self.trees.append(t)
        return t

    def remove_tree(self, tree):
        '''Remove a tree from the forest.'''
        tree.decrement(tree.root.id)
        self.trees.remove(tree)

    def commit(self):
        '''Make sure all changes are stored into the node store.'''
        self.node_store.push_upload_queue()
        self.node_store.set_metadata('last_id', self.last_id)
        root_ids = ','.join('%d' % t.root.id 
                            for t in self.trees 
                            if t.root is not None)
        self.node_store.set_metadata('root_ids', root_ids)
        self.node_store.set_metadata('key_size', 
                                     self.node_store.codec.key_bytes)
        self.node_store.set_metadata('node_size', self.node_store.node_size)
        self.node_store.save_metadata()
        self.node_store.save_refcounts()


def open_forest(key_size=None, node_size=None, codec=None, node_store=None, 
                **kwargs):
    '''Create a new Factory instance.
    
    key_size, node_size must be given with every call.
    codec is the class to be used for the node codec, defaults to
    larch.NodeCodec. Similarly, node_store is the node store class,
    defaults to larch.NodeStoreDisk.
    
    All other keyword arguments are given the thoe node_store
    class initializer.
    
    '''

    assert key_size is not None
    assert node_size is not None

    codec = codec or larch.NodeCodec
    node_store = node_store or larch.NodeStoreDisk

    c = codec(key_size)
    ns = node_store(node_size, c, **kwargs)
    
    def check_size(keyname, wanted, exception):
        if keyname not in ns.get_metadata_keys():
            return
        value = int(ns.get_metadata(keyname))
        if value != wanted:
            raise exception(value, wanted)

    check_size('key_size', key_size, BadKeySize)
    check_size('node_size', node_size, BadNodeSize)

    return Forest(ns)

