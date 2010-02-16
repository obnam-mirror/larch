import unittest

import btree


class EmptyNodeTests(unittest.TestCase):

    def setUp(self):
        self.empty = btree.Node(0, [], True)

    def test_has_zero_length(self):
        self.assertEqual(len(self.empty), 0)
        
    def test_has_zero_size(self):
        self.assertEqual(self.empty.size(), 0)

    def test_has_no_keys(self):
        self.assertEqual(self.empty.keys(), [])
        
    def test_lookup_raises_error_for_nonexistent_key(self):
        self.assertRaises(KeyError, self.empty.lookup, '0')
        
    def test_is_leaf(self):
        self.assert_(self.empty.isleaf)

    def test_does_not_find_higher_key(self):
        self.assertRaises(KeyError, self.empty.find_next_highest_key, '')
        
    
class NodeTests(unittest.TestCase):

    def setUp(self):
        self.keys = ['foo', 'bar', 'foobar']
        self.values = ['FOO', 'BAR', 'FOOBAR']
        self.nodeid = 12765
        self.node = btree.Node(self.nodeid, 
                               zip(self.keys, self.values),
                               False)
 
    def test_has_right_id(self):
        self.assertEqual(self.node.id, self.nodeid)
        
    def test_has_right_keys(self):
        self.assertEqual(sorted(self.node.keys()), sorted(self.keys))
        
    def test_has_right_length(self):
        self.assertEqual(len(self.node), len(self.keys))
        
    def test_has_approximately_right_size(self):
        bytes = sum(len(s) for s in self.keys + self.values)
        self.assert_(bytes <= self.node.size() <= 2 * bytes)
        
    def test_finds_value(self):
        self.assertEqual(self.node.lookup('foo'), 'FOO')

    def test_finds_next_highest_key(self):
        self.assertEqual(self.node.find_next_highest_key('bar'), 'foo')
        
    def test_does_not_find_higher_key_than_largest_key(self):
        self.assertRaises(KeyError, self.node.find_next_highest_key,
                          sorted(self.keys)[-1])

        
class BtreeTests(unittest.TestCase):

    def setUp(self):
        self.tree = btree.Btree(nodesize=16)

    def test_has_zero_height_initially(self):
        self.assertEqual(self.tree.height, 0)
        
    def test_looking_up_nonexistent_key_raises_keyerror(self):
        self.assertRaises(KeyError, self.tree.lookup, 'a')
        
    def test_inserting_key_works(self):
        self.tree.insert('a', 'foo')
        self.assertEqual(self.tree.lookup('a'), 'foo')

