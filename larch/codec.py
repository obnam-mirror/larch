# Copyright 2010  Lars Wirzenius
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import struct

import larch


class CodecError(larch.Error):

    def __init__(self, msg):
        self.msg = msg


class NodeCodec(object):

    '''Encode and decode nodes from their binary format.
    
    Node identifiers are assumed to fit into 64 bits.
    
    Leaf node values are assumed to fit into 4 gibibytes.
    
    '''
    
    format = 1

    # We use the struct module for encoding and decoding. For speed,
    # we construct the format string all at once, so that there is only
    # one call to struct.pack or struct.unpack for one node. This brought
    # a thousand time speedup over doing it one field at a time. However,
    # the code is not quite as clear as it might be, what with no symbolic
    # names for anything is used anymore. Patches welcome.
    
    def __init__(self, key_bytes):
        self.key_bytes = key_bytes
        self.leaf_header = struct.Struct('!4sQI')
        self.index_header = struct.Struct('!4sQI')
        # space for key and length of value is needed for each pair
        self.leaf_pair_fixed_size = key_bytes + struct.calcsize('!I')
        self.index_pair_size = key_bytes + struct.calcsize('!Q')
        
    def leaf_size(self, keys, values):
        '''Return size of a leaf node with the given pairs.'''
        return (self.leaf_header.size + len(keys) * self.leaf_pair_fixed_size +
                len(''.join([value for value in values])))

    def leaf_size_delta_add(self, old_size, value):
        '''Return size of node that gets a new key/value pair added.
        
        ``old_size`` is the old size of the node. The key must not already
        have existed in the node.
        
        '''
        
        delta = self.leaf_pair_fixed_size + len(value)
        return old_size + delta

    def leaf_size_delta_replace(self, old_size, old_value, new_value):
        '''Return size of node that gets a value replaced.'''
        
        return old_size + len(new_value) - len(old_value)

    def encode_leaf(self, node):
        '''Encode a leaf node as a byte string.'''

        keys = node.keys()
        values = node.values()
        return (self.leaf_header.pack('ORBL', node.id, len(keys)) +
                ''.join(keys) +
                struct.pack('!%dI' % len(values), *map(len, values)) +
                ''.join(values))

    def decode_leaf(self, encoded):
        '''Decode a leaf node from its encoded byte string.'''

        buf = buffer(encoded)
        cookie, node_id, num_pairs = self.leaf_header.unpack_from(buf)
        if cookie != 'ORBL':
            raise CodecError('Leaf node does not begin with magic cookie '
                             '(should be ORBL, is %s)' % repr(cookie))
        fmt = '!' + ('%ds' % self.key_bytes) * num_pairs + 'I' * num_pairs
        items = struct.unpack_from(fmt, buf, self.leaf_header.size)
        keys = items[:num_pairs]
        lengths = items[num_pairs:num_pairs*2]
        values = []
        offset = self.leaf_header.size + self.leaf_pair_fixed_size * num_pairs
        append = values.append
        for length in lengths:
            append(encoded[offset:offset + length])
            offset += length
        return larch.LeafNode(node_id, keys, values)

    def max_index_pairs(self, node_size):
        '''Return number of index pairs that fit in a node of a given size.'''
        return (node_size - self.index_header.size) / self.index_pair_size
        
    def index_size(self, keys, values):
        '''Return size of an index node with the given pairs.'''
        return self.index_header.size + self.index_pair_size * len(keys)

    def encode_index(self, node):
        '''Encode an index node as a byte string.'''

        keys = node.keys()
        child_ids = node.values()
        return (self.index_header.pack('ORBI', node.id, len(keys)) +
                ''.join(keys) +
                struct.pack('!%dQ' % len(child_ids), *child_ids))

    def decode_index(self, encoded):
        '''Decode an index node from its encoded byte string.'''

        buf = buffer(encoded)
        cookie, node_id, num_pairs = self.index_header.unpack_from(buf)
        if cookie != 'ORBI':
            raise CodecError('Index node does not begin with magic cookie '
                             '(should be ORBI, is %s)' % repr(cookie))
        fmt = '!' + ('%ds' % self.key_bytes) * num_pairs + 'Q' * num_pairs
        items = struct.unpack_from(fmt, buf, self.index_header.size)
        keys = items[:num_pairs]
        child_ids = items[num_pairs:]
        assert len(keys) == len(child_ids)
        for x in child_ids:
            assert type(x) == int
        return larch.IndexNode(node_id, keys, child_ids)

    def encode(self, node):
        '''Encode a node of any type.'''
        if isinstance(node, larch.LeafNode):
            return self.encode_leaf(node)
        else:
            return self.encode_index(node)

    def decode(self, encoded):
        '''Decode node of any type.'''
        if encoded.startswith('ORBL'):
            return self.decode_leaf(encoded)
        elif encoded.startswith('ORBI'):
            return self.decode_index(encoded)
        else:
            raise CodecError('Unknown magic cookie in encoded node (%s)' %
                             repr(encoded[:4]))

    def size(self, node):
        '''Return encoded size of a node, regardless of type.'''
        keys = node.keys()
        values = node.values()
        if isinstance(node, larch.LeafNode):
            return self.leaf_size(keys, values)
        else:
            return self.index_size(keys, values)

