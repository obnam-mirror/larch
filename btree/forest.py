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


import btree


class Forest(object):

    '''A collection of BTrees in the same node store.'''

    def __init__(self, node_store):
        self.node_store = node_store
        self.trees = []
        self.last_id = 0
        self.read_metadata()

    def read_metadata(self):
        if 'last_id' in self.node_store.get_metadata_keys():
            self.last_id = int(self.node_store.get_metadata('last_id'))
    
    def store_metadata(self):
        self.node_store.set_metadata('last_id', self.last_id)
        self.node_store.save_metadata()

    def new_id(self):
        '''Generate next node id for this forest.'''
        self.last_id += 1
        self.store_metadata()
        return self.last_id

    def new_tree(self, old=None):
        '''Create a new tree.

        If old is None, a completely new tree is created. Otherwise,
        a clone of an existing one is created.

        '''

        if old:
            t = btree.BTree(self, self.node_store, old.root_id)
        else:
            t = btree.BTree(self, self.node_store, None)
        self.trees.append(t)
        return t
