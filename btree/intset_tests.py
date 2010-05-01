import unittest

import intset


class IntSetTests(unittest.TestCase):

    def setUp(self):
        self.set = intset.IntSet()

    def test_empty_set_round_trip(self):
        empty = intset.IntSet()
        new = intset.IntSet()
        new.update_from_string(str(empty))
        self.assertEqual(new, empty)

    def test_one_item_round_trip(self):
        a = intset.IntSet([0])
        b = intset.IntSet()
        b.update_from_string(str(a))
        self.assertEqual(a, b)

    def test_large_round_trip(self):
        a = intset.IntSet(range(1000))
        b = intset.IntSet()
        b.update_from_string(str(a))
        self.assertEqual(a, b)

    def test_large_superdense_set_has_small_string_representation(self):
        a = intset.IntSet(range(1000))
        self.assert_(len(a) <= len('0-1000'))

    def test_large_semidense_set_has_small_string_representation(self):
        a = intset.IntSet(range(1000) + range(10*1000, 100*1000))
        self.assert_(len(a) <= len('0-1000,10000-100000'))

