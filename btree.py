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
        elif key < node.key1:
            raise KeyError(key)
        elif node.key2 is None or key < node.key2:
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
        elif node.key2 is None:
            if key < node.key1:
                new_child = self._insert(None, key, value)
                return IndexNode(new_child.key1, new_child, 
                                 node.key1, node.child1)
            else:
                new_child = self._insert(node.child1, key, value)
                return IndexNode(new_child.key1, new_child, None, None)
        else:
            if key < node.key2:
                new_child = self._insert(node.child1, key, value)
                return IndexNode(new_child.key1, new_child,
                                 node.key2, node.child2)
            else:
                new_child = self._insert(node.child2, key, value)
                return IndexNode(node.key1, node,
                                 new_child.key1, new_child)
        
    def remove(self, key):
        self.root = self._remove(self.root, key)
        
    def _remove(self, node, key):
        if node is None:
            raise KeyError(key)
        elif key == node.key:
            return Node(key, None, node.child1, node.child2)
        elif key < node.key:
            new_child = self._remove(node.child1, key)
            return Node(node.key, node.value, new_child, node.child2)
        else:
            new_child = self._remove(node.child2, key)
            return Node(node.key, node.value, node.child1, new_child)

