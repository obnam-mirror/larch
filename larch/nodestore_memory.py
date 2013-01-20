# Copyright 2010, 2011  Lars Wirzenius
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


class NodeStoreMemory(larch.NodeStore):

    '''An implementation of larch.NodeStore API for in-memory storage.
    
    All nodes are kept in memory. This is for demonstration and testing
    purposes only.
    
    '''
    
    def __init__(self,allow_writes, node_size, codec):
        larch.NodeStore.__init__(
            self, allow_writes=allow_writes, node_size=node_size, codec=codec)
        self.nodes = dict()
        self.refcounts = dict()
        self.metadata = dict()
        
    def get_metadata_keys(self):
        return self.metadata.keys()
        
    def get_metadata(self, key):
        return self.metadata[key]
        
    def set_metadata(self, key, value):
        self.metadata[key] = value

    def remove_metadata(self, key):
        del self.metadata[key]
        
    def put_node(self, node):
        node.frozen = True
        self.nodes[node.id] = node
        
    def get_node(self, node_id):
        if node_id in self.nodes:
            return self.nodes[node_id]
        else:
            raise larch.NodeMissing(repr(self), node_id)

    def start_modification(self, node):
        node.frozen = False
    
    def remove_node(self, node_id):
        if node_id in self.nodes:
            del self.nodes[node_id]
        else:
            raise larch.NodeMissing(repr(self), node_id)
        
    def list_nodes(self):
        return self.nodes.keys()

    def get_refcount(self, node_id):
        return self.refcounts.get(node_id, 0)

    def set_refcount(self, node_id, refcount):
        self.refcounts[node_id] = refcount
