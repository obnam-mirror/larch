import unittest

import btree


class EmptyNodeTests(unittest.TestCase):

    def setUp(self):
        self.empty = btree.Node(0, [])

    def test_has_zero_length(self):
        self.assertEqual(len(self.empty), 0)
        
    def test_has_zero_size(self):
        self.assertEqual(self.empty.size(), 0)

    def test_has_no_keys(self):
        self.assertEqual(self.empty.keys(), [])
        
    def test_lookup_raises_error_for_nonexistent_key(self):
        self.assertRaises(KeyError, self.empty.lookup, '0')
        
    
class NodeTests(unittest.TestCase):

    def setUp(self):
        self.keys = ['foo', 'bar', 'foobar']
        self.values = ['FOO', 'BAR', 'FOOBAR']
        self.nodeid = 12765
        self.node = btree.Node(self.nodeid, zip(self.keys, self.values))
 
    def test_has_right_id(self):
        self.assertEqual(self.node.id, self.nodeid)
        
    def test_has_right_keys(self):
        self.assertEqual(sorted(self.node.keys()), sorted(self.keys))
        
    def test_has_right_length(self):
        self.assertEqual(len(self.node), len(self.keys))
        
    def test_has_approximately_right_size(self):
        bytes = sum(len(s) for s in self.keys + self.values)
        self.assert_(bytes <= self.node.size() <= 2 * bytes)
