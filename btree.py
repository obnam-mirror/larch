class LeafNode(dict):

    def keys(self):
        return sorted(dict.keys(self))


class IndexNode(dict):

    def keys(self):
        return sorted(dict.keys(self))
       

class BinarySearchTree(object):

    def __init__(self, fanout):
        self.root = IndexNode([])
        self.fanout = fanout
        
    def lookup(self, key):
        return self._lookup(self.root, key)

    def _lookup(self, node, key):
        if isinstance(node, LeafNode):
            return node[key]
        else:
            k = self.find_key_for_child_containing(node, key)
            if k is None:
                raise KeyError(key)
            else:
                return self._lookup(node[k], key)

    def find_key_for_child_containing(self, node, key):
        for k in reversed(node.keys()):
            if key >= k:
                return k
        return None

    def insert(self, key, value):
        a, b = self._insert(self.root, key, value)
        if b is None:
            self.root = a
        else:
            self.root = IndexNode([(a.keys()[0], a),
                                   (b.keys()[0], b)])

    def _insert(self, node, key, value):
        if isinstance(node, LeafNode):
            return self._insert_into_leaf(node, key, value)
        else:
            return self._insert_into_index(node, key, value)

    def _insert_into_leaf(self, leaf, key, value):
        pairs = [(k, leaf[k]) for k in leaf if k != key] + [(key, value)]
        pairs.sort()
        if len(pairs) <= self.fanout:
            return LeafNode(pairs), None
        else:
            n = len(pairs) / 2
            leaf1 = LeafNode(pairs[:n])
            leaf2 = LeafNode(pairs[n:])
            return leaf1, leaf2

    def _insert_into_index(self, node, key, value):
        k = self.find_key_for_child_containing(node, key)
        if k is None:
            child = LeafNode([(key, value)])
            pairs = [(kk, node[kk]) for kk in node] + [(key, child)]
            pairs.sort()
            if len(pairs) <= self.fanout:
                return IndexNode(pairs), None
            else:
                n = len(pairs) / 2
                return IndexNode(pairs[:n]), IndexNode(pairs[n:])
        else:
            a, b = self._insert(node[k], key, value)
            pairs = [(kk, node[kk]) for kk in node if kk != k]
            if a is not None:
                pairs += [(a.keys()[0], a)]
            if b is not None:
                pairs += [(b.keys()[0], b)]
            pairs.sort()
            if len(pairs) <= self.fanout:
                return IndexNode(pairs), None
            else:
                pairs.sort()
                n = len(pairs) / 2
                return IndexNode(pairs[:n]), IndexNode(pairs[n:])
        
    def remove(self, key):
        self.root = self._remove(self.root, key)
        if self.root is None:
            self.root = IndexNode([])
        
    def _remove(self, node, key):
        if isinstance(node, LeafNode):
            return self._remove_from_leaf(node, key)
        else:
            return self._remove_from_index(node, key)

    def _remove_from_leaf(self, node, key):
        if key in node:
            pairs = [(k, node[k]) for k in node if k != key]
            if pairs:
                return LeafNode(pairs)
            else:
                return None
        else:
            raise KeyError(key)

    def _remove_from_index(self, node, key):
        k = self.find_key_for_child_containing(node, key)
        if k is None:
            raise KeyError(key)
        else:
            child = self._remove(node[k], key)
            pairs = [(kk, node[kk]) for kk in node if kk != k]
            if child is not None:
                pairs += [(child.keys()[0], child)]
            pairs.sort()
            if pairs:
                return IndexNode(pairs)
            else:
                return None

