def size_of_pair(key, value):
    '''Give size of a pair in bytes, when encoded for on-disk format.'''
    return len(key) + len(value)


class LeafNode(dict):

    '''A leaf node in a Tree.
    
    A leaf node contains key/value pairs. Both are strings.
    
    '''
    
    isleaf = True

    def size(self):
        '''Return number of bytes required to store this node.'''
        return sum(size_of_pair(key, value) 
                   for key, value in self.iteritems())

    def find_surrounding_keys(self, key):
        keys = sorted(self.keys())
        if not keys:
            return None, None
        if key < keys[0]:
            return None, keys[0]
        if key >= keys[-1]:
            return keys[-1], None
        for i, k in enumerate(keys):
            if k <= key < keys[i+1]:
                return k, keys[i+1]
        assert False

        
class IndexNode(LeafNode):

    isleaf = False

    def size(self):
        return sum(size_of_pair('%d' % key, value)
                   for key, value in self.iteritems())


class Btree(object):

    def __init__(self, nodesize):
        self.nodesize = nodesize
        self.root = IndexNode([])

    def __getitem__(self, key):
        node = self.root
        while not node.isleaf:
            lo, hi = node.find_surrounding_keys(key)
            if lo is None:
                raise KeyError(key)
            node = node.lookup(lo)
        return node[key]

    def insert(self, key, value):
        a, b = self._insert(self.root, key, value)
        if b is None:
            self.root = a
        else:
            self.root = Node([a, b])

    def _insert(self, node, key, value):
        if node.isleaf:
            if self.fits(node, key, len(value)):
                return Node(node.items() + [(key, value)]), None
            else:
                return self.split(node, key, value)
        else:
            lo, hi = node.find_surrounding_keys(key)
            if lo:
                
            if self.fits(node, key, self.idsize):
                if key in self.node:
                    a, b = self._insert(self.node[key], key, value)
                    pairs = [(k, v) 
                             for k, v in node.items() + [(key, 
                else:
            else:

    def fits(self, node, key, value_size):
        more_size = size_of_pair(key, '*' * value_size)
        return node.size() + more_size <= self.nodesize
        
    def split(self, node, key, value):
        pairs = node.items() + [(key, value)]
        pairs.sort()
        for i in range(len(pairs)):
            n = Node(pairs[:i])
            if n.size() >= self.nodesize / 2:
                break
        return n, Node(pairs[i:])

    def idstr(self, nodeid):
        return '%0*d' % (self.idsize, nodeid)
        
    idsize = 8

