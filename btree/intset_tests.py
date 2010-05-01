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
        self.assert_(len(str(a)) <= len('0-1000'))

    def test_large_semidense_set_has_small_string_representation(self):
        a = intset.IntSet(range(1000) + range(10*1000, 100*1000))
        self.assert_(len(str(a)) <= len('0-1000,10000-100000'))


class IntSetSetTests(unittest.TestCase):

    def setUp(self):
        self.set = intset.IntSet()

    def test_empty_set_has_zero_length(self):
        self.assertEqual(len(self.set), 0)

    def test_set_of_one_has_length_one(self):
        self.set.add(42)
        self.assertEqual(len(self.set), 1)

    def test_empty_set_is_equal_to_itself(self):
        self.assert_(self.set == self.set)

    def test_set_of_one_is_equal_to_itself(self):
        self.set.add(42)
        self.assert_(self.set == self.set)

    def test_identical_sets_are_equal(self):
        set1 = intset.IntSet([1, 2, 3])
        set2 = intset.IntSet()
        set2.add(1)
        set2.add(3)
        set2.add(2)
        self.assert_(set1 == set2)

    def test_adding_in_different_order_results_in_same_set(self):
        ref = intset.IntSet([1, 2, 3])
        seqs = [(1, 2, 3),
                (1, 3, 2),
                (2, 1, 3),
                (2, 3, 1),
                (3, 1, 2),
                (3, 2, 1)]
        for seq in seqs:
            new = intset.IntSet()
            for item in seq:
                new.add(item)
            self.assertEqual(ref.ranges, new.ranges)

    def test_adding_item_twice_results_in_same_set(self):
        ref = intset.IntSet([1])
        self.set.add(1)
        self.set.add(1)
        self.assertEqual(ref.ranges, self.set.ranges)

