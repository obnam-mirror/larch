import struct

import btree


class NodeCodec(object):

    '''Encode and decode nodes from their binary format.
    
    Node identifiers are assumed to fit into 64 bits.
    
    Leaf node values are assumed to fit into 65535 bytes.
    
    '''
    
    def __init__(self, key_bytes):
        self.key_bytes = key_bytes
        self.index_header_format = '!cQ'
        self.index_format = '!%dsQ' % key_bytes
        self.leaf_header_format = '!cQ'
        self.leaf_format = '!%dsH%%ds' % key_bytes
        
        self.id_size = struct.calcsize('!Q')
        self.index_header_size = struct.calcsize(self.index_header_format)
        self.index_pair_size = struct.calcsize(self.index_format)
        self.leaf_header_size = struct.calcsize(self.leaf_header_format)

    def leaf_size(self, pairs):
        '''Return size of a leaf node with the given pairs.'''
        return (self.leaf_header_size +
                sum(struct.calcsize(self.leaf_format % len(value))
                    for key, value in pairs))

    def max_index_pairs(self, node_size): # pragma: no cover
        '''Return number of index pairs that fit in a node of a given size.'''
        return (node_size - self.index_header_size) / self.index_pair_size

    def encode_leaf(self, node):
        '''Encode a leaf node as a byte string.'''
        
        parts = [struct.pack(self.leaf_header_format, 'L', node.id)]
        for key, value in node.iteritems():
            parts.append(self.format_leaf_pair(key, value))
        return ''.join(parts)

    def encode_index(self, node):
        '''Encode an index node as a byte string.'''
        
        parts = [struct.pack(self.index_header_format, 'I', node.id)]
        for key, child_id in node.iteritems():
            parts.append(self.format_index_pair(key, child_id))
        return ''.join(parts)

    def encode(self, node):
        if isinstance(node, btree.LeafNode):
            return self.encode_leaf(node)
        else:
            return self.encode_index(node)

    def format_index_pair(self, key, child_id):
        return struct.pack(self.index_format, key, child_id)

    def format_leaf_pair(self, key, value):
        return struct.pack(self.leaf_format % len(value), 
                           key, len(value), value)

    def decode_id(self, encoded):
        '''Return leading node identifier.'''
        assert len(encoded) >= self.id_size
        (node_id,) = struct.unpack('!Q', encoded[:self.id_size])
        return node_id, encoded[self.id_size:]
        
    def decode_leaf(self, encoded):
        '''Decode a leaf node from its encoded byte string.'''

        assert encoded.startswith('L')
        node_id, rest = self.decode_id(encoded[1:])
        
        pairs = []
        while rest:
            n = struct.calcsize(self.leaf_format % 0)
            (key, value_size, value) = struct.unpack(self.leaf_format % 0 ,
                                                     rest[:n])
            n += value_size
            s, rest = rest[:n], rest[n:]
            (key, value_size, value) = \
                struct.unpack(self.leaf_format % value_size, s)
            pairs.append((key, value))
        
        return btree.LeafNode(node_id, pairs)
        
    def decode_index(self, encoded):
        '''Decode an index node from its encoded byte string.'''

        assert encoded.startswith('I')
        node_id, rest = self.decode_id(encoded[1:])
        
        pairs = []
        pair_size = struct.calcsize(self.index_format)
        while rest:
            s, rest = rest[:pair_size], rest[pair_size:]
            pairs.append(struct.unpack(self.index_format, s))
        
        return btree.IndexNode(node_id, pairs)

    def decode(self, encoded):
        if encoded.startswith('L'):
            return self.decode_leaf(encoded)
        else:
            return self.decode_index(encoded)

