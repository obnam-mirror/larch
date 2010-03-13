class LeafNode(dict):

    def keys(self):
        return sorted(dict.keys(self))


class IndexNode(dict):

    def __init__(self, pairs):
        for key, child in pairs:
            assert type(key) == str
            assert isinstance(child, IndexNode) or isinstance(child, LeafNode),\
                'pairs: %s' % repr(pairs)
        dict.__init__(self, pairs)

    def keys(self):
        return sorted(dict.keys(self))
       

class BTree(object):

    def __init__(self, fanout):
        self.root = IndexNode([])
        self.fanout = fanout
        self.min_index_length = self.fanout
        self.max_index_length = 2 * self.fanout + 1
        
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

    def pairs(self, node, exclude=None):
        if exclude is None:
            exclude = []
        return sorted((key, node[key]) for key in node if key not in exclude)

    def first_key(self, node):
        return node.keys()[0]

    def insert(self, key, value):
        a, b = self._insert(self.root, key, value)
        if b is None:
            self.root = a
        else:
            self.root = IndexNode([(self.first_key(a), a),
                                   (self.first_key(b), b)])

    def _insert(self, node, key, value):
        if isinstance(node, LeafNode):
            return self._insert_into_leaf(node, key, value)
        elif len(node) == 0:
            return self._insert_into_empty_root(key, value)
        elif len(node) == self.max_index_length:
            return self._insert_into_full_index(node, key, value)
        else:
            return self._insert_into_nonfull_index(node, key, value)

    def _insert_into_leaf(self, leaf, key, value):
        pairs = sorted(self.pairs(leaf, exclude=[key]) + [(key, value)])
        if len(pairs) <= self.fanout:
            return LeafNode(pairs), None
        else:
            n = len(pairs) / 2
            leaf1 = LeafNode(pairs[:n])
            leaf2 = LeafNode(pairs[n:])
            return leaf1, leaf2

    def _insert_into_empty_root(self, key, value):
        leaf = LeafNode([(key, value)])
        return IndexNode([(self.first_key(leaf), leaf)]), None

    def _insert_into_full_index(self, node, key, value):
        # A full index node needs to be split, then key/value inserted into
        # one of the halves.
        pairs = self.pairs(node)
        n = len(pairs) / 2
        node1 = IndexNode(pairs[:n])
        node2 = IndexNode(pairs[n:])
        if key < self.first_key(node2):
            a, b = self._insert(node1, key, value)
            assert b is None
            return a, node2
        else:
            a, b = self._insert(node2, key, value)
            assert b is None
            return node1, a
    
    def _insert_into_nonfull_index(self, node, key, value):        
        # Insert into correct child, get up to two replacements for
        # that child.

        k = self.find_key_for_child_containing(node, key)
        if k is None:
            k = self.first_key(node)

        a, b = self._insert(node[k], key, value)
        assert a is not None
        pairs = self.pairs(node, exclude=[k]) + [(self.first_key(a), a)]
        if b is not None:
            pairs += [(self.first_key(b), b)]
        pairs.sort()
        assert len(pairs) <= self.max_index_length
        return IndexNode(pairs), None

    def remove(self, key):
        self.root = self._remove(self.root, key)
        if self.root is None:
            self.root = IndexNode([])
        
    def _remove(self, node, key):
        if isinstance(node, LeafNode):
            return self._remove_from_leaf(node, key)
        else:
            k = self.find_key_for_child_containing(node, key)
            if k is None:
                raise KeyError(key)
            elif len(node[k]) <= self.min_index_length and len(node) > 1:
                return self._remove_from_minimal_index(node, key, k) 
            else:
                return self._remove_from_nonminimal_index(node, key, k)

    def _remove_from_leaf(self, node, key):
        if key in node:
            pairs = self.pairs(node, exclude=[key])
            if pairs:
                return LeafNode(pairs)
            else:
                return None
        else:
            print; print 'key %s not in %s' % (key, node.keys())
            raise KeyError(key)
    
    def merge(self, n1, n2):
        if isinstance(n1, IndexNode):
            assert isinstance(n2, IndexNode)
            return IndexNode(self.pairs(n1) + self.pairs(n2))
        else:
            assert isinstance(n1, LeafNode)
            assert isinstance(n2, LeafNode)
            return LeafNode(self.pairs(n1) + self.pairs(n2))

    def sibling_length(self, node, keys, index):
        if index < 0 or index >= len(node):
            return None
        else:
            return node[keys[index]]

    def _remove_from_minimal_index(self, node, key, child_key):
        child = self._remove(node[child_key], key)
        
        if child is None:
            others = self.pairs(node, exclude=[child_key])
            if not others:
                # Only child got removed.
                return None
            else:
                return IndexNode(others)
        else:
            keys = node.keys()
            child_index = keys.index(child_key)
            
            prev_index = child_index - 1
            next_index = child_index + 1
            
            prev_len = self.sibling_length(node, keys, prev_index)
            next_len = self.sibling_length(node, keys, next_index)
            
            prev_ok = (prev_len is not None and 
                       prev_len < self.max_index_length)
            next_ok = (next_len is not None and 
                       next_len < self.max_index_length)

            if keys == [child_key]:
                return IndexNode([(self.first_key(child), child)])
            elif prev_ok and next_ok:
                if prev_len < next_len:
                    merge_index = prev_index
                else:
                    merge_index = next_index
            elif prev_ok:
                merge_index = prev_index
            elif next_ok:
                merge_index = next_index
            else:
                return IndexNode(self.pairs(node, exclude=[child_key]) + 
                                 [(self.first_key(child), child)])

            assert merge_index
            
            merge_key = keys[merge_index]
            merge_node = node[merge_key]
            merged = self.merge(child, merge_node)
            others = self.pairs(node, exclude=[child_key, merge_key])
            return IndexNode(others + [(self.first_key(merged), merged)])
        
    def _remove_from_nonminimal_index(self, node, key, child_key):
        child = self._remove(node[child_key], key)
        pairs = self.pairs(node, exclude=[child_key])
        if child is not None:
            pairs += [(self.first_key(child), child)]
        pairs.sort()
        if pairs:
            return IndexNode(pairs)
        else:
            return None

