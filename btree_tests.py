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
