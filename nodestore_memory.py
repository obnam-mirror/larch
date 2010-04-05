import btree

class NodeStoreMemory(btree.NodeStore):

    '''An implementation of btree.NodeStore API for in-memory storage.
    
    All nodes are kept in memory. This is for demonstration and testing
    purposes only.
    
    '''
    
    def __init__(self, node_size):
        btree.NodeStore.__init__(self, node_size)
        self.nodes = dict()
        
    def put_node(self, node_id, encoded_node):
        if len(encoded_node) > self.node_size:
            raise btree.NodeTooBig(node_id, len(encoded_node))
        self.nodes[node_id] = encoded_node
        
    def get_node(self, node_id):
        if node_id in self.nodes:
            return self.nodes[node_id]
        else:
            raise btree.NodeMissing(node_id)
    
    def remove_node(self, node_id):
        del self.nodes[node_id]
        
    def list_nodes(self):
        return self.nodes.keys()
