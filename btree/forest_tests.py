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

import btree


class ForestTests(unittest.TestCase):

    def setUp(self):
        self.codec = btree.NodeCodec(3)
        self.ns = btree.NodeStoreMemory(64, self.codec)
        self.forest = btree.Forest(self.ns)

    def test_new_node_ids_grow(self):
        id1 = self.forest.new_id()
        id2 = self.forest.new_id()
        self.assertEqual(id1 + 1, id2)

    def test_has_no_trees_initially(self):
        self.assertEqual(self.forest.trees, [])

    def test_creates_a_tree(self):
        t = self.forest.new_tree()
        self.assert_(isinstance(t, btree.BTree))
        self.assertEqual(self.forest.trees, [t])

    def test_clones_a_tree(self):
        t1 = self.forest.new_tree()
        t2 = self.forest.new_tree(t1)
        self.assertNotEqual(t1.root.id, t2.root.id)

    def test_clones_can_be_changed_independently(self):
        t1 = self.forest.new_tree()
        t2 = self.forest.new_tree(t1)
        t1.insert('foo', 'foo')
        self.assertNotEqual(t1.root.id, t2.root.id)

    def test_clones_do_not_clash_in_new_node_ids(self):
        t1 = self.forest.new_tree()
        t2 = self.forest.new_tree(t1)
        node1 = t1.new_leaf([], [])
        node2 = t2.new_leaf([], [])
        self.assertEqual(node1.id + 1, node2.id)

    def test_is_persistent(self):
        t1 = self.forest.new_tree()
        t1.insert('foo', 'bar')
        self.forest.commit()

        f2 = btree.Forest(self.ns)
        self.assertEqual([t.root.id for t in f2.trees], [t1.root.id])

    def test_removes_trees(self):
        t1 = self.forest.new_tree()
        self.forest.remove_tree(t1)
        self.assertEqual(self.forest.trees, [])

    def test_remove_tree_removes_nodes_for_tree_as_well(self):
        t = self.forest.new_tree()
        t.insert('foo', 'bar')
        self.forest.commit()
        self.assertNotEqual(self.ns.list_nodes(), [])
        self.forest.remove_tree(t)
        self.assertEqual(self.ns.list_nodes(), [])

    def test_changes_work_across_commit(self):
        t1 = self.forest.new_tree()
        t1.insert('000', 'foo')
        t1.insert('001', 'bar')
        t2 = self.forest.new_tree(t1)
        t2.insert('002', 'foobar')
        t2.remove('000')
        self.forest.commit()

        f2 = btree.Forest(self.ns)
        t1a, t2a = f2.trees
        self.assertEqual(t1.root.id, t1a.root.id)
        self.assertEqual(t2.root.id, t2a.root.id)
        self.assertEqual(t1a.lookup('000'), 'foo')
        self.assertEqual(t1a.lookup('001'), 'bar')
        self.assertRaises(KeyError, t2a.lookup, '000')
        self.assertEqual(t2a.lookup('001'), 'bar')
        self.assertEqual(t2a.lookup('002'), 'foobar')

    def test_committing_single_empty_tree_works(self):
        self.forest.new_tree()
        self.assertEqual(self.forest.commit(), None)

    def test_read_metadata_works_after_removed_and_committed(self):
        t1 = self.forest.new_tree()
        t1.insert('foo', 'foo')
        self.forest.commit()

        self.forest.remove_tree(t1)
        self.forest.commit()

        f2 = btree.Forest(self.ns)
        self.assertEqual(f2.trees, [])


class ForestFactoryTests(unittest.TestCase):

    def setUp(self):
        self.key_size = 3
        self.node_size = 64
        self.factory = btree.ForestFactory(codec=btree.NodeCodec,
                                           node_store=btree.NodeStoreMemory)
        
    def test_creates_new_forest(self):
        f = self.factory.new(self.key_size, self.node_size)
        self.assertEqual(f.node_store.codec.key_bytes, self.key_size)
        self.assertEqual(f.node_store.node_size, self.node_size)

