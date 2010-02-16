class Node(object):

    '''A node in a Tree.'''

    def __init__(self, nodeid, pairs):
        pass

    def __len__(self):
        '''Return number of keys in this node.'''
        return 0

    def size(self):
        '''Return number of bytes required to store this node.'''
        return 0

    def keys(self):
        '''Return all keys in this node.'''
        return []

    def lookup(self, key):
        '''Return value corresponding to a given key in this node.
        
        If key is not in this node, raise KeyError.
        
        '''
        
        raise KeyError(key)


#class Tree(object):
#    '''A B-tree variant.'''
#    def __init__(self, keysize, nodesize):
#    def insert(self, key, value):
#    def lookup(self, key):
#    def remove(self, key):

