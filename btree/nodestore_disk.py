import ConfigParser
import os

import btree

class NodeStoreDisk(btree.NodeStore):

    '''An implementation of btree.NodeStore API for on-disk storage.
    
    The caller will specify a directory in which the nodes will be stored.
    Each node is stored in its own file, named after the node identifier.
    
    '''
    
    def __init__(self, dirname, node_size, codec):
        btree.NodeStore.__init__(self, node_size, codec)
        self.dirname = dirname
        self.metadata_name = os.path.join(dirname, 'metadata')
        self.metadata = None

    def _load_metadata(self):
        if self.metadata is None:
            self.metadata = ConfigParser.ConfigParser()
            self.metadata.add_section('metadata')
            if os.path.exists(self.metadata_name):
                f = file(self.metadata_name)
                self.metadata.readfp(f)
                f.close()

    def _save_metadata(self):
        self._load_metadata()
        f = file(self.metadata_name + '_new', 'w')
        self.metadata.write(f)
        f.close()
        os.rename(self.metadata_name + '_new', self.metadata_name)

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
        self._save_metadata()

    def remove_metadata(self, key):
        self._load_metadata()
        if self.metadata.has_option('metadata', key):
            self.metadata.remove_option('metadata', key)
        else:
            raise KeyError(key)
        self._save_metadata()

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
