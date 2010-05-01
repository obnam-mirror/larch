class IntSet(set):

    '''A dense set of integers.

    This is like a plain set, except all values must be integers, and
    there are two additional methods for encoding the set as a text
    string, and decoding from that representation.

    '''

    def __str__(self):
        return ''

    def update_from_string(self, string):
        '''Add values from an IntSet represented as a string.'''

