import os

import btree

class NodeStoreDisk(btree.NodeStore):

    '''An implementation of btree.NodeStore API for on-disk storage.
    
    The caller will specify a directory in which the nodes will be stored.
    Each node is stored in its own file, named after the node identifier.
    
    '''
    
    def __init__(self, dirname, node_size):
        btree.NodeStore.__init__(self, node_size)
        self.dirname = dirname
        self.metadata_name = os.path.join(dirname, 'metadata')

    def set_metadata(self, blob):
        file(self.metadata_name, 'w').write(blob)

    def get_metadata(self):
        if os.path.exists(self.metadata_name):
            return file(self.metadata_name).read()
        else:
            return ''

    def pathname(self, node_id):
        return os.path.join(self.dirname, '%d.node' % node_id)
        
    def put_node(self, node_id, encoded_node):
        if len(encoded_node) > self.node_size:
            raise btree.NodeTooBig(node_id, len(encoded_node))
        name = self.pathname(node_id)
        if node_id != 0 and os.path.exists(name):
            raise btree.NodeExists(node_id)
        file(name, 'w').write(encoded_node)
        
    def get_node(self, node_id):
        name = self.pathname(node_id)
        if os.path.exists(name):
            return file(name).read()
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
