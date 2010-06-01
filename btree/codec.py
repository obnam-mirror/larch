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

import btree


class CodecError(Exception):

    pass


class NodeCodec(object):

    '''Encode and decode nodes from their binary format.
    
    Node identifiers are assumed to fit into 64 bits.
    
    Leaf node values are assumed to fit into 65535 bytes.
    
    '''

    # We use the struct module for encoding and decoding. For speed,
    # we construct the format string all at once, so that there is only
    # one call to struct.pack or struct.unpack for one node. This brought
    # a thousand time speedup over doing it one field at a time. However,
    # the code is not quite as clear as it might be, what with no symbolic
    # names for anything is used anymore. Patches welcome.
    
    def __init__(self, key_bytes):
        self.key_bytes = key_bytes
        self.leaf_header_size = struct.calcsize('!4sQI')
        # space for key and length of value is needed for each pair
        self.pair_fixed_size = key_bytes + struct.calcsize('!I')
        
    def leaf_size(self, pairs):
        '''Return size of a leaf node with the given pairs.'''
        return (self.leaf_header_size + len(pairs) * self.pair_fixed_size +
                len(''.join([value for key, value in pairs])))

    def encode_leaf(self, node):
        '''Encode a leaf node as a byte string.'''

        keys, values = zip(*node.pairs())
        return (struct.pack('!4sQI', 'ORBL', node.id, len(keys)) +
                ''.join(keys) +
                struct.pack('!%dI' % len(values), *map(len, values)) +
                ''.join(values))

    def decode_leaf(self, encoded):
        '''Decode a leaf node from its encoded byte string.'''

        buf = buffer(encoded)
        cookie, node_id, num_pairs = struct.unpack_from('!4sQI', buf)
        if cookie != 'ORBL':
            raise CodecError('Leaf node does not begin with magic cookie '
                             '(should be ORBL, is %s)' % repr(cookie))
        fmt = ('!4sQI' + ('%ds' % self.key_bytes) * num_pairs + 
                'I' * num_pairs)
        items = struct.unpack_from(fmt, buf)
        keys = items[3:3+num_pairs]
        lengths = items[3+num_pairs:3+num_pairs*2]
        offsets = [0]
        for i in range(1, len(lengths)):
            offsets.append(offsets[-1] + lengths[i-1])

        values = buffer(encoded, struct.calcsize(fmt))
        pairs = [(keys[i], values[offsets[i]:offsets[i] + lengths[i]]) 
                    for i in range(len(keys))]

        return btree.LeafNode(node_id, pairs)

    def max_index_pairs(self, node_size): # pragma: no cover
        '''Return number of index pairs that fit in a node of a given size.'''
        index_header_size = struct.calcsize('!4sQI')
        index_pair_size = struct.calcsize('%dsQ' % self.key_bytes)
        return (node_size - index_header_size) / index_pair_size
        
    def index_size(self, pairs):
        '''Return size of an inex node with the given pairs.'''
        fmt = self.index_format(pairs)
        return struct.calcsize(fmt)

    def index_format(self, pairs):
        return ('!4sQI' + ('%ds' % self.key_bytes) * len(pairs) + 
                'Q' * len(pairs))
        
    def encode_index(self, node):
        '''Encode an index node as a byte string.'''

        pairs = node.pairs()
        fmt = self.index_format(pairs)
        return struct.pack(fmt, *(['ORBI', node.id, len(pairs)] +
                                  [key for key, child_id in pairs] +
                                  [child_id for key, child_id in pairs]))

    def decode_index(self, encoded):
        '''Decode an index node from its encoded byte string.'''

        buf = buffer(encoded)
        cookie, node_id, num_pairs = struct.unpack_from('!4sQI', buf)
        if cookie != 'ORBI':
            raise CodecError('Index node does not begin with magic cookie '
                             '(should be ORBI, is %s)' % repr(cookie))
        fmt = ('!4sQI' + 
               ('%ds' % self.key_bytes) * num_pairs + 
               'Q' * num_pairs)
        items = struct.unpack(fmt, encoded)
        keys = items[3:3+num_pairs]
        child_ids = items[3+num_pairs:]
        assert len(keys) == len(child_ids)
        for x in child_ids:
            assert type(x) == int
        return btree.IndexNode(node_id, zip(keys, child_ids))

    def encode(self, node):
        if isinstance(node, btree.LeafNode):
            return self.encode_leaf(node)
        else:
            return self.encode_index(node)

    def decode(self, encoded):
        if encoded.startswith('ORBL'):
            return self.decode_leaf(encoded)
        elif encoded.startswith('ORBI'):
            return self.decode_index(encoded)
        else:
            raise CodecError('Unknown magic cookie in encoded node (%s)' %
                             repr(encoded[:4]))

    def size(self, node):
        if isinstance(node, btree.LeafNode):
            return self.leaf_size(node.pairs())
        else:
            return self.index_size(node.pairs())

