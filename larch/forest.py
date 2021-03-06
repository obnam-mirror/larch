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


import tracing

import larch


class MetadataMissingKey(larch.Error):

    def __init__(self, key_name):
        self.msg = 'larch forest metadata missing "%s"' % key_name


class BadKeySize(larch.Error):

    def __init__(self, store_key_size, wanted_key_size):
        self.msg = ('Node store has key size %s, program wanted %s' %
                    (store_key_size, wanted_key_size))


class BadNodeSize(larch.Error):

    def __init__(self, store_node_size, wanted_node_size):
        self.msg = ('Node store has node size %s, program wanted %s' %
                    (store_node_size, wanted_node_size))


class Forest(object):

    '''A collection of related B-trees.
    
    Trees in the same forest can share nodes. Cloned trees are always
    created in the same forest as the original.
    
    Cloning trees is very fast: only the root node is modified.
    Trees can be modified in place. Modifying a tree is done
    using copy-on-write, so modifying a clone does not modify
    the original (and vice versa). You can have up to 65535 
    clones of a tree.
    
    The list of trees in the forest is stored in the ``trees``
    property as a list of trees in the order in which they were
    created.
    
    '''

    def __init__(self, node_store):
        tracing.trace('new larch.Forest with node_store=%s' % repr(node_store))
        self.node_store = node_store
        self.trees = []
        self.last_id = 0
        self._read_metadata()

    def _read_metadata(self):
        tracing.trace('reading metadata')
        keys = self.node_store.get_metadata_keys()
        tracing.trace('metadata keys: %s' % repr(keys))
        if 'last_id' in keys:
            self.last_id = int(self.node_store.get_metadata('last_id'))
            tracing.trace('last_id = %s' % self.last_id)
        if 'root_ids' in keys:
            s = self.node_store.get_metadata('root_ids')
            tracing.trace('root_ids: %s', s)
            if s.strip():
                root_ids = [int(x) for x in s.split(',')]
                self.trees = [larch.BTree(self, self.node_store, root_id)
                              for root_id in root_ids]
                tracing.trace('root_ids: %s' % repr(root_ids))
            else:
                self.trees = []
                tracing.trace('empty root_ids')
    
    def new_id(self):
        '''Generate next node id for this forest.
        
        Trees should use this whenever they create new nodes.
        The ids generated by this method are guaranteed to
        be unique (as long as commits happen OK).
        
        '''

        self.last_id += 1
        tracing.trace('new id = %d' % self.last_id)
        return self.last_id

    def new_tree(self, old=None):
        '''Create a new tree.

        If old is None, a completely new tree is created. Otherwise,
        a clone of an existing one is created.

        '''

        tracing.trace('new tree (old=%s)' % repr(old))
        if old:
            old_root = self.node_store.get_node(old.root.id)
            keys = old_root.keys()
            values = old_root.values()
        else:
            keys = []
            values = []
        t = larch.BTree(self, self.node_store, None)
        t._set_root(t._new_index(keys, values))
        self.trees.append(t)
        tracing.trace('new tree root id: %s' % t.root.id)
        return t

    def remove_tree(self, tree):
        '''Remove a tree from the forest.'''
        tracing.trace('removing tree with root id %d' % tree.root.id)
        tree._decrement(tree.root.id)
        self.trees.remove(tree)

    def commit(self):
        '''Make sure all changes are stored into the node store.
        
        Changes made to the forest are guaranteed to be persistent
        only if commit is called successfully.
        
        '''
        tracing.trace('committing forest')
        self.node_store.set_metadata('last_id', self.last_id)
        root_ids = ','.join('%d' % t.root.id 
                            for t in self.trees 
                            if t.root is not None)
        self.node_store.set_metadata('root_ids', root_ids)
        self.node_store.set_metadata('key_size', 
                                     self.node_store.codec.key_bytes)
        self.node_store.set_metadata('node_size', self.node_store.node_size)
        self.node_store.save_refcounts()
        self.node_store.commit()


def open_forest(allow_writes=None, key_size=None, node_size=None, codec=None, 
                node_store=None, **kwargs):
    '''Create or open a forest.
    
    ``key_size`` and ``node_size`` are retrieved from the forest, unless
    given. If given, they must match exactly. If the forest does not
    yet exist, the sizes **must** be given.

    ``codec`` is the class to be used for the node codec, defaults to
    ``larch.NodeCodec``. Similarly, ``node_store`` is the node store class,
    defaults to ``larch.NodeStoreDisk``.
    
    All other keyword arguments are given the the ``node_store``
    class initializer.
    
    '''

    tracing.trace('opening forest')
    
    assert allow_writes is not None

    codec = codec or larch.NodeCodec
    node_store = node_store or larch.NodeStoreDisk

    if key_size is None or node_size is None:
        # Open a temporary node store for reading metadata.
        # For this, we can use any values for node and key sizes,
        # since we won't be accessing nodes or keys.
        c_temp = codec(42)
        ns_temp = node_store(False, 42, c_temp, **kwargs)

        if 'key_size' not in ns_temp.get_metadata_keys():
            raise MetadataMissingKey('key_size')
        if 'node_size' not in ns_temp.get_metadata_keys():
            raise MetadataMissingKey('node_size')
        
        if key_size is None:
            key_size = int(ns_temp.get_metadata('key_size'))
        if node_size is None:
            node_size = int(ns_temp.get_metadata('node_size'))
    
    c = codec(key_size)
    ns = node_store(allow_writes, node_size, c, **kwargs)
    
    def check_size(keyname, wanted, exception):
        if keyname not in ns.get_metadata_keys():
            return
        value = int(ns.get_metadata(keyname))
        if value != wanted:
            raise exception(value, wanted)

    check_size('key_size', key_size, BadKeySize)

    return Forest(ns)

