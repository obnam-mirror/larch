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


import unittest

import larch


class LRUCacheTests(unittest.TestCase):

    def setUp(self):
        self.cache = larch.LRUCache(4)
        self.cache.remove_hook = self.remove_hook
        self.cache.forget_hook = self.forget_hook
        self.removed = []
        self.forgotten = []

    def remove_hook(self, key, obj):
        self.removed.append((key, obj))

    def forget_hook(self, key, obj):
        self.forgotten.append((key, obj))

    def test_does_not_have_remove_hook_initially(self):
        cache = larch.LRUCache(4)
        self.assertEqual(cache.remove_hook, None)

    def test_sets_remove_hook_via_init(self):
        cache = larch.LRUCache(4, remove_hook=self.remove_hook)
        self.assertEqual(cache.remove_hook, self.remove_hook)

    def test_does_not_have_forget_hook_initially(self):
        cache = larch.LRUCache(4)
        self.assertEqual(cache.forget_hook, None)

    def test_sets_forget_hook_via_init(self):
        cache = larch.LRUCache(4, forget_hook=self.forget_hook)
        self.assertEqual(cache.forget_hook, self.forget_hook)

    def test_does_not_contain_object_initially(self):
        self.assertEqual(self.cache.get('foo'), None)

    def test_does_contain_object_after_it_is_added(self):
        self.cache.add('foo', 'bar')
        self.assertEqual(self.cache.get('foo'), 'bar')

    def test_oldest_object_dropped_first(self):
        for i in range(self.cache.max_size + 1):
            self.cache.add(i, i)
        self.assertEqual(self.cache.get(0), None)
        self.assertEqual(self.forgotten, [(0, 0)])
        for i in range(1, self.cache.max_size + 1):
            self.assertEqual(self.cache.get(i), i)

    def test_getting_object_prevents_it_from_being_dropped(self):
        for i in range(self.cache.max_size + 1):
            self.cache.add(i, i)
            self.cache.get(0)
        self.assertEqual(self.cache.get(1), None)
        self.assertEqual(self.forgotten, [(1, 1)])
        for i in [0] + range(2, self.cache.max_size + 1):
            self.assertEqual(self.cache.get(i), i)

    def test_adding_key_twice_changes_object(self):
        self.cache.add('foo', 'foo')
        self.cache.add('foo', 'bar')
        self.assertEqual(self.cache.get('foo'), 'bar')

    def test_removes_object(self):
        self.cache.add('foo', 'bar')
        gotit = self.cache.remove('foo')
        self.assertEqual(gotit, True)
        self.assertEqual(self.cache.get('foo'), None)
        self.assertEqual(self.removed, [('foo', 'bar')])

    def test_remove_returns_False_for_unknown_object(self):
        self.assertEqual(self.cache.remove('foo'), False)

    def test_removes_oldest_object(self):
        self.cache.add(0, 0)
        self.cache.add(1, 1)
        self.assertEqual(self.cache.remove_oldest(), (0, 0))
        self.assertEqual(self.cache.get(0), None)

    def test_length_is_initially_zero(self):
        self.assertEqual(len(self.cache), 0)
    
    def test_length_is_correct_after_adds(self):
        self.cache.add(0, 0)
        self.assertEqual(len(self.cache), 1)

    def test_has_initially_no_keys(self):
        self.assertEqual(self.cache.keys(), [])
    
    def test_has_keys_after_add(self):
        self.cache.add(0, 1)
        self.assertEqual(self.cache.keys(), [0])

