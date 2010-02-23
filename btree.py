class LeafNode(object):

    def __init__(self, key, value):
        self.key = key
        self.value = value
        

class IndexNode(object):

    def __init__(self, key1, child1, key2, child2):
        self.key1 = key1
        self.child1 = child1
        self.key2 = key2
        self.child2 = child2
        

class BinarySearchTree(object):

    def __init__(self):
        self.root = None
        
    def lookup(self, key):
        return self._lookup(self.root, key)

    def _lookup(self, node, key):
        if node is None:
            raise KeyError(key)
        elif isinstance(node, LeafNode):
            if key != node.key or node.value is None:
                raise KeyError(key)
            return node.value
        elif key < node.key2:
            return self._lookup(node.child1, key)
        else:
            return self._lookup(node.child2, key)

    def insert(self, key, value):
        self.root = self._insert(self.root, key, value)

    def _insert(self, node, key, value):
        if node is None:
            return LeafNode(key, value)
        elif isinstance(node, LeafNode):
            if key == node.key:
                return LeafNode(key, value)
            else:
                new_leaf = LeafNode(key, value)
                if key < node.key:
                    return IndexNode(key, new_leaf, node.key, node)
                else:
                    return IndexNode(node.key, node, key, new_leaf)
        else:
            assert node.key2 is not None
            if key < node.key2:
                new_child = self._insert(node.child1, key, value)
                return IndexNode(new_child.key1, new_child,
                                 node.key2, node.child2)
            else:
                new_child = self._insert(node.child2, key, value)
                return IndexNode(node.key1, node.child1,
                                 new_child.key1, new_child)
        
    def remove(self, key):
        self.root = self._remove(self.root, key)
        
    def _remove(self, node, key):
        if node is None:
            raise KeyError(key)
        elif isinstance(node, LeafNode):
            if key == node.key:
                return LeafNode(key, None)
            else:
                raise KeyError(key)
        elif key < node.key2:
            new_child = self._remove(node.child1, key)
            if isinstance(new_child, LeafNode):
                return IndexNode(new_child.key, new_child,
                                 node.key2, node.child2)
            else:
                return IndexNode(new_child.key1, new_child, 
                                 node.key2, node.child2)
        else:
            new_child = self._remove(node.child2, key)
            if isinstance(new_child, LeafNode):
                return IndexNode(node.key1, node.child1,
                                 new_child.key, new_child)
            else:
                return IndexNode(node.key1, node.child1,
                                 new_child.key1, new_child)

