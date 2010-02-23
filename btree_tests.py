import unittest

import btree


class LeafNodeTests(unittest.TestCase):

    def setUp(self):
        self.key = 'key'
        self.value = 'value'
        self.leaf = btree.LeafNode(self.key, self.value)

    def test_has_key(self):
        self.assertEqual(self.leaf.key, self.key)

    def test_has_value(self):
        self.assertEqual(self.leaf.value, self.value)

