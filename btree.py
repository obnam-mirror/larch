class Node(object):

    '''A node in a Tree.
    
    A node contains some number of key/value pairs. Both keys and
    values are supposed to be byte strings. All keys are supposed
    to be the same size.
    
    '''

    def __init__(self, nodeid, pairs, isleaf):
        self.id = nodeid
        self.pairs = pairs
        self.isleaf = isleaf

    def __len__(self):
        '''Return number of keys in this node.'''
        return len(self.pairs)

    def size(self):
        '''Return number of bytes required to store this node.'''
        return sum(len(key) + len(value) for key, value in self.pairs)

    def keys(self):
        '''Return all keys in this node.'''
        return [key for key, value in self.pairs]

    def items(self):
        '''Return list of key/value pairs.'''
        return self.pairs

    def lookup(self, key):
        '''Return value corresponding to a given key in this node.
        
        If key is not in this node, raise KeyError.
        
        '''

        for candidate, value in self.pairs:
            if candidate == key:
                return value 
        raise KeyError(key)

    def find_next_highest_key(self, key):
        '''Return smallest key that is bigger than given key.
        
        Raise KeyError if not found.
        
        '''
        
        for k in sorted(self.keys()):
            if k > key:
                return k
        raise KeyError(key)

    def __contains__(self, key):
        try:
            self.lookup(key)
        except KeyError:
            return False
        else:
            return True


class Btree(object):

    '''A B-tree variant.
    
    The tree stores key/value pairs, using Node instances (but
    this is invisible to the user). The tree is balanced.
    
    '''

    def __init__(self, nodesize):
        self.nodesize = nodesize
        self.height = 0
        self.latest_nodeid = 0
        self.root = None

    def new_node(self, old_node, new_pairs):
        if old_node:
            pairs = [(key, old_node.lookup(key)) for key in old_node.keys]
        else:
            pairs = []
        pairs += new_pairs
        pairs.sort()
        self.latest_nodeid += 1
        return Node(self.latest_nodeid, pairs)

    def lookup(self, key):
        '''Return value associated with key or raise KeyError if missing.'''
        node = self.root
        while node:
            if node.isleaf:
                return node.lookup(key)
            else:
                keys = node.keys()
                if key < keys[0]:
                    break
                if key > keys[-1]:
                    node = node.lookup(keys[-1])
                else:
                    next = node.find_next_highest_key(key)
                    node = node.lookup(next)
        raise KeyError(key)

    def insert(self, key, value):
        '''Insert key/value pair into tree.
        
        If key already exists in tree, replace it.
        
        '''

        if not self.root:
            self._root = self.new_node(None, [(key, value)])
        else:
            self.root = self._insert(self.root, key, value)
    
    def _insert(self, node, key, value):
        if node.size() + len(key) + len(value) < self.nodesize:
            return self.new_node(node, [(key, value)])
        else:
            return self.split_node(node, key, value)

    def split_node(self, node, key, value):
        pairs = sorted(node.items() + [(key, value)])
        i = len(pairs) / 2
        assert i > 0
        n1 = self.new_node(None, pairs[:i])
        n2 = self.new_node(None, pairs[i:])
        return self.new_node(None, [(pairs[0][0], n1), (pairs[i][0], n2)])
            
#    def remove(self, key):

