import unittest

import bsearch


class BsearchTests(unittest.TestCase):

    def setUp(self):
        self.array = [1, 3, 5, 7, 9]

    def test_finds_each_element(self):
        for i, key in enumerate(self.array):
            self.assertEqual(bsearch.bsearch(self.array, key), (i, i))

    def test_finds_surrounding_elements_for_zero(self):
        self.assertEqual(bsearch.bsearch(self.array, 0), (None, 0))

    def test_finds_surrounding_elements_for_two(self):
        self.assertEqual(bsearch.bsearch(self.array, 2), (0, 1))

    def test_finds_surrounding_elements_for_four(self):
        self.assertEqual(bsearch.bsearch(self.array, 4), (1, 2))

    def test_finds_surrounding_elements_for_six(self):
        self.assertEqual(bsearch.bsearch(self.array, 6), (2, 3))

    def test_finds_surrounding_elements_for_eight(self):
        self.assertEqual(bsearch.bsearch(self.array, 8), (3, 4))

    def test_finds_surrounding_elements_for_ten(self):
        self.assertEqual(bsearch.bsearch(self.array, 10), (4, None))
        
    def test_finds_surrounding_elements_for_empty_array(self):
        self.assertEqual(bsearch.bsearch([], 0), (None, None))
