class LeafNode(object):

    def __init__(self, key, value):
        self.key = key
        self.value = value
        

class IndexNode(object):

    def __init__(self, child1, child2):
        self.child1 = child1
        self.child2 = child2
        

class BinarySearchTree(object):

    def __init__(self):
        self.root = None
        
    def lookup(self, key):
        raise KeyError(key)

    def insert(self, key, value):
        if self.root is None:
            self.root = LeafNode(key, value)
        else:
            self.root = self._insert(self.root, key, value)

    def _insert(self, node, key, value):
        if node is None:
            return LeafNode(key, value)
        elif isinstance(node, LeafNode):
            if node.key == key:
                return LeafNode(key, value)
            else:
                raise Exception('internal error')
        else:
            if node.child2 is None:
        
    def remove(self, key):
        raise KeyError(key)
