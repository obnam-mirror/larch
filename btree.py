class Node(object):

    '''A node in a Tree.
    
    A node contains some number of key/value pairs. Both keys and
    values are supposed to be byte strings. All keys are supposed
    to be the same size.
    
    '''

    def __init__(self, nodeid, pairs):
        self.id = nodeid
        self.pairs = pairs

    def __len__(self):
        '''Return number of keys in this node.'''
        return len(self.pairs)

    def size(self):
        '''Return number of bytes required to store this node.'''
        return sum(len(key) + len(value) for key, value in self.pairs)

    def keys(self):
        '''Return all keys in this node.'''
        return [key for key, value in self.pairs]

    def lookup(self, key):
        '''Return value corresponding to a given key in this node.
        
        If key is not in this node, raise KeyError.
        
        '''

        for candidate, value in self.pairs:
            if candidate == key:
                return value 
        raise KeyError(key)


#class Tree(object):
#    '''A B-tree variant.'''
#    def __init__(self, keysize, nodesize):
#    def insert(self, key, value):
#    def lookup(self, key):
#    def remove(self, key):

