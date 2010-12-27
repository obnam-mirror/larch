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


import random
import sys
import unittest

import btree


class DummyForest(object):

    def __init__(self):
        self.last_id = 0

    def new_id(self):
        self.last_id += 1
        return self.last_id


class DummyNodeStore(object):

    def __init__(self, node_size, codec):
        self.node_size = node_size
        self.codec = codec
        self.nodes = dict()
        self.metadata = dict()
        self.refcounts = dict()

    def max_index_pairs(self):
        return 4

    def get_metadata_keys(self):
        return self.metadata.keys()

    def get_metadata(self, key):
        return self.metadata[key]
        
    def set_metadata(self, key, value):
        self.metadata[key] = value

    def save_metadata(self):
        pass
    
    def put_node(self, node):
        self.nodes[node.id] = node
        
    def get_node(self, node_id):
        return self.nodes[node_id]
        
    def find_nodes(self):
        return self.nodes.keys()

    def remove_node(self, node_id):
        del self.nodes[node_id]
        self.set_refcount(node_id, 0)

    def get_refcount(self, node_id):
        return self.refcounts.get(node_id, 0)

    def set_refcount(self, node_id, refcount):
        self.refcounts[node_id] = refcount


class KeySizeMismatchTests(unittest.TestCase):

    def setUp(self):
        self.err = btree.KeySizeMismatch('foo', 4)
        
    def test_error_message_contains_key(self):
        self.assert_('foo' in str(self.err))
        
    def test_error_message_contains_wanted_size(self):
        self.assert_('4' in str(self.err))


class BTreeTests(unittest.TestCase):

    def setUp(self):
        # We use a small node size so that all code paths are traversed
        # during testing. Use coverage.py to make sure they do.
        self.codec = btree.NodeCodec(3)
        self.ns = DummyNodeStore(64, self.codec)
        self.forest = DummyForest()
        self.tree = btree.BTree(self.forest, self.ns, None)
        self.dump = False

    def test_creates_leaf(self):
        leaf = self.tree.new_leaf([])
        self.assertEqual(leaf, self.tree.get_node(leaf.id))

    def test_knows_node_with_refcount_1_can_be_modified_in_place(self):
        node = self.tree.new_leaf([])
        self.ns.set_refcount(node.id, 1)
        self.assert_(self.tree.node_can_be_modified_in_place(node))

    def test_knows_node_with_refcount_2_cannot_be_modified_in_place(self):
        node = self.tree.new_leaf([])
        self.ns.set_refcount(node.id, 2)
        self.assertFalse(self.tree.node_can_be_modified_in_place(node))

    def test_shadow_returns_leaf_itself_when_refcount_is_1(self):
        leaf = self.tree.new_leaf([])
        self.ns.set_refcount(leaf.id, 1)
        clone = self.tree._shadow(leaf)
        self.assertEqual(leaf.id, clone.id)

    def test_shadow_returns_new_leaf_when_refcount_is_2(self):
        leaf = self.tree.new_leaf([])
        self.ns.set_refcount(leaf.id, 2)
        clone = self.tree._shadow(leaf)
        self.assertNotEqual(leaf.id, clone.id)

    def test_shadow_returns_index_itself_when_refcount_is_1(self):
        index = self.tree.new_index([])
        self.ns.set_refcount(index.id, 1)
        clone = self.tree._shadow(index)
        self.assertEqual(index.id, clone.id)

    def test_shadow_returns_new_index_when_refcount_is_2(self):
        index = self.tree.new_index([])
        self.ns.set_refcount(index.id, 2)
        clone = self.tree._shadow(index)
        self.assertNotEqual(index.id, clone.id)

    def test_shadow_increments_childrens_refcounts(self):
        leaf = self.tree.new_leaf([('foo', 'bar')])
        index = self.tree.new_index([(leaf.first_key(), leaf.id)])
        self.assertEqual(self.ns.get_refcount(leaf.id), 1)
        self.ns.set_refcount(index.id, 2)
        clone = self.tree._shadow(index)
        self.assertEqual(self.ns.get_refcount(leaf.id), 2)

    def test_creates_index(self):
        index = self.tree.new_index([])
        self.assertEqual(index, self.tree.get_node(index.id))

    def test_new_index_increments_childrens_refcounts(self):
        leaf = self.tree.new_leaf([])
        self.assertEqual(self.ns.get_refcount(leaf.id), 0)
        self.tree.new_index([('foo', leaf.id)])
        self.assertEqual(self.ns.get_refcount(leaf.id), 1)

    def test_new_root_does_not_return_it(self):
        self.assertEqual(self.tree.new_root([]), None)

    def test_creates_root_from_nothing(self):
        self.tree.new_root([])
        self.assertEqual(self.tree.root.id, 1) # first node always id 1

    def test_insert_changes_root_id(self):
        self.tree.insert('foo', 'bar')
        self.assertNotEqual(self.tree.root.id, 0)

    def test_is_empty(self):
        self.assertEqual(self.tree.root, None)
        
    def test_lookup_for_missing_key_raises_error(self):
        self.assertRaises(KeyError, self.tree.lookup, 'foo')

    def test_lookup_with_wrong_size_key_raises_error(self):
        self.assertRaises(btree.KeySizeMismatch, self.tree.lookup, '')

    def test_insert_inserts_key(self):
        self.tree.insert('foo', 'bar')
        self.assertEqual(self.tree.lookup('foo'), 'bar')

    def test_insert_inserts_empty_value(self):
        self.tree.insert('foo', '')
        self.assertEqual(self.tree.lookup('foo'), '')

    def test_insert_replaces_value_for_existing_key(self):
        self.tree.insert('foo', 'foo')
        self.tree.insert('foo', 'bar')
        self.assertEqual(self.tree.lookup('foo'), 'bar')

    def test_insert_with_wrong_size_key_raises_error(self):
        self.assertRaises(btree.KeySizeMismatch, self.tree.insert, '', '')

    def test_remove_from_empty_tree_raises_keyerror(self):
        self.assertRaises(KeyError, self.tree.remove, 'foo')

    def test_remove_of_missing_key_raises_keyerror(self):
        self.tree.insert('bar', 'bar')
        self.assertRaises(KeyError, self.tree.remove, 'foo')

    def test_remove_removes_key(self):
        self.tree.insert('foo', 'bar')
        self.tree.remove('foo')
        self.assertRaises(KeyError, self.tree.lookup, 'foo')

    def get_roots_first_child(self):
        child_key, child_id = self.tree.root.pairs()[0]
        return self.ns.get_node(child_id)
        
    def test_remove_makes_tree_lower(self):
        self.tree.insert('foo', 'bar')
        self.assertEqual(type(self.get_roots_first_child()), btree.LeafNode)
        root_key = self.tree.root.pairs()[0][0]
        old_root_id = self.tree.root.id
        self.tree.new_root([(root_key, self.tree.root.id)])
        self.ns.set_refcount(old_root_id, 1)
        self.assertEqual(type(self.get_roots_first_child()), btree.IndexNode)
        self.tree._reduce_height()
        self.assertEqual(type(self.get_roots_first_child()), btree.LeafNode)
        
    def test_remove_does_not_make_tree_lower_when_children_are_shared(self):
        self.tree.insert('foo', 'bar')
        root_key = self.tree.root.pairs()[0][0]
        old_root_id = self.tree.root.id
        self.tree.new_root([(root_key, self.tree.root.id)])
        self.ns.set_refcount(old_root_id, 2)
        self.assertEqual(len(self.tree.root), 1)
        self.assertEqual(type(self.get_roots_first_child()), btree.IndexNode)
        self.tree._reduce_height()
        self.assertEqual(type(self.get_roots_first_child()), btree.IndexNode)

    def test_remove_with_wrong_size_key_raises_error(self):
        self.assertRaises(btree.KeySizeMismatch, self.tree.remove, '')

    def keys_are_in_range(self, node, lower, upper, level=0):
        indent = 2
        if isinstance(node, btree.LeafNode):
            if self.dump:
                print '%*sleaf keys %s' % (level*indent, '', node.keys())
            for key in node.keys():
                if key < lower or key >= upper:
                    return False
        else:
            keys = node.keys()
            if self.dump: print '%*sin range; index keys = %s' % (level*indent, '', keys), 'lower..upper:', lower, upper
            if keys != sorted(keys):
                return False
            for i, key in enumerate(keys):
                if key < lower or key >= upper:
                    return False
                if i+1 == len(keys):
                    up = upper
                else:
                    up = keys[i+1]
                if self.dump: print '%*sin child, keys should be in %s..%s' % (level*indent, '', key, up)
                if not self.keys_are_in_range(self.tree.get_node(node[key]), key, up, level+1):
                    return False
        return True

    def find_largest_key(self, node):
        if isinstance(node, btree.LeafNode):
            return max(node.keys())
        else:
            return max(node.keys() + 
                       [self.find_largest_key(self.tree.get_node(node[key]))
                        for key in node.keys()])

    def nextkey(self, key):
        assert type(key) == str
        if key == '':
            return '\0'
        if key[-1] == '\xff':
            return key + '\0'
        else:
            return key[:-1] + chr(ord(key[-1]) + 1)

    def proper_search_tree(self, node):
        if not node.keys():
            return True
        minkey = node.keys()[0]
        maxkey = self.find_largest_key(node)
        if self.dump: print; print 'proper tree', minkey, self.nextkey(maxkey)
        return self.keys_are_in_range(node, minkey, self.nextkey(maxkey))

    def test_insert_many_respects_ordering_requirement(self):
        ints = range(100)
        random.shuffle(ints)
        for i in ints:
            key = '%03d' % i
            value = key
            self.tree.insert(key, value)
            self.assertEqual(self.tree.lookup(key), value)
            self.assert_(self.proper_search_tree(self.tree.root),
                         'key#%d failed' % (1 + ints.index(i)))

    def test_remove_many_works(self):
        ints = range(100)
        random.shuffle(ints)
        for i in ints:
            key = '%03d' % i
            value = key
            self.tree.insert(key, value)
            self.assertEqual(self.tree.lookup(key), value)
            self.tree.remove(key)
            self.assertRaises(KeyError, self.tree.lookup, key)
            self.assert_(self.proper_search_tree(self.tree.root),
                         msg='insert of %d in %s failed to keep tree ok' %
                         (i, ints))

    def dump_tree(self, node, f=sys.stdout, level=0):
        if not self.dump:
            return
        indent = 4
        if isinstance(node, btree.LeafNode):
            f.write('%*sLeaf:' % (level*indent, ''))
            for key in node.keys():
                f.write(' %s=%s' % (key, node[key]))
            f.write('\n')
        else:
            assert isinstance(node, btree.IndexNode)
            f.write('%*sIndex:\n' % (level*indent, ''))
            for key in node.keys():
                f.write('%*s%s:\n' % ((level+1)*indent, '', key))
                self.dump_tree(self.tree.get_node(node[key]), level=level+2)

    def test_insert_many_remove_many_works(self):
        keys = ['%03d' % i for i in range(100)]
        random.shuffle(keys)
        for key in keys:
            self.tree.insert(key, key)
            self.assert_(self.proper_search_tree(self.tree.root))
        if self.dump:
            print
            print
            self.dump_tree(self.tree.root)
            print
        for key in keys:
            if self.dump:
                print
                print 'removing', key
                self.dump_tree(self.tree.root)
            try:
                self.tree.remove(key)
            except:
                self.dump = True
                self.dump_tree(self.tree.root)
                ret = self.proper_search_tree(self.tree.root)
                print 'is it?', ret
                raise
            self.assert_(self.proper_search_tree(self.tree.root))
            if self.dump:
                print
                print
        self.assertEqual(self.tree.root.keys(), [])
        
    def test_remove_merges_leaf_with_left_sibling(self):
        keys = ['%03d' % i for i in range(3)]
        for key in keys:
            self.tree.insert(key, 'x')
        self.assertEqual(self.tree.remove(keys[1]), None)
        
    def test_persists(self):
        self.tree.insert('foo', 'bar')
        tree2 = btree.BTree(self.forest, self.ns, self.tree.root.id)
        self.assertEqual(tree2.lookup('foo'), 'bar')

    def test_last_node_id_persists(self):
        self.tree.insert('foo', 'bar') # make tree has root
        node1 = self.tree.new_leaf([])
        tree2 = btree.BTree(self.forest, self.ns, self.tree.root.id)
        node2 = tree2.new_leaf([])
        self.assertEqual(node1.id + 1, node2.id)

    def test_lookup_range_returns_empty_list_if_nothing_found(self):
        self.assertEqual(self.tree.lookup_range('bar', 'foo'), [])

    def create_tree_for_range(self):
        for key in ['%03d' % i for i in range(2, 10, 2)]:
            self.tree.insert(key, key)

    def test_lookup_range_returns_empty_list_if_before_smallest_key(self):
        self.create_tree_for_range()
        self.assertEqual(self.tree.lookup_range('000', '001'), [])

    def test_lookup_range_returns_empty_list_if_after_largest_key(self):
        self.create_tree_for_range()
        self.assertEqual(self.tree.lookup_range('010', '999'), [])

    def test_lookup_range_returns_empty_list_if_between_keys(self):
        self.create_tree_for_range()
        self.assertEqual(self.tree.lookup_range('003', '003'), [])

    def test_lookup_range_returns_single_item_in_range(self):
        self.create_tree_for_range()
        self.assertEqual(self.tree.lookup_range('002', '002'), 
                          [('002', '002')])

    def test_lookup_range_returns_single_item_in_range_exclusive(self):
        self.create_tree_for_range()
        self.assertEqual(self.tree.lookup_range('001', '003'), 
                          [('002', '002')])

    def test_lookup_range_returns_two_items_in_range(self):
        self.create_tree_for_range()
        self.assertEqual(sorted(self.tree.lookup_range('002', '004')), 
                          [('002', '002'), ('004', '004')])

    def test_lookup_range_returns_all_items_in_range(self):
        self.create_tree_for_range()
        self.assertEqual(sorted(self.tree.lookup_range('000', '999')), 
                          [('002', '002'), 
                           ('004', '004'),
                           ('006', '006'),
                           ('008', '008')])

    def test_range_is_empty_returns_true_for_empty_tree(self):
        self.assertTrue(self.tree.range_is_empty('bar', 'foo'))
        
    def test_range_is_empty_works_for_nonempty_tree(self):
        self.create_tree_for_range()
        
        self.assertEqual(self.tree.range_is_empty('000', '000'), True)
        self.assertEqual(self.tree.range_is_empty('000', '001'), True)
        self.assertEqual(self.tree.range_is_empty('000', '002'), False)
        self.assertEqual(self.tree.range_is_empty('000', '003'), False)
        self.assertEqual(self.tree.range_is_empty('000', '004'), False)
        self.assertEqual(self.tree.range_is_empty('000', '005'), False)
        self.assertEqual(self.tree.range_is_empty('000', '006'), False)
        self.assertEqual(self.tree.range_is_empty('000', '007'), False)
        self.assertEqual(self.tree.range_is_empty('000', '008'), False)
        self.assertEqual(self.tree.range_is_empty('000', '009'), False)
        self.assertEqual(self.tree.range_is_empty('000', '010'), False)
        self.assertEqual(self.tree.range_is_empty('000', '011'), False)
        self.assertEqual(self.tree.range_is_empty('000', '999'), False)
        
        self.assertEqual(self.tree.range_is_empty('001', '001'), True)
        self.assertEqual(self.tree.range_is_empty('001', '002'), False)
        self.assertEqual(self.tree.range_is_empty('001', '003'), False)
        self.assertEqual(self.tree.range_is_empty('001', '004'), False)
        self.assertEqual(self.tree.range_is_empty('001', '005'), False)
        self.assertEqual(self.tree.range_is_empty('001', '006'), False)
        self.assertEqual(self.tree.range_is_empty('001', '007'), False)
        self.assertEqual(self.tree.range_is_empty('001', '008'), False)
        self.assertEqual(self.tree.range_is_empty('001', '009'), False)
        self.assertEqual(self.tree.range_is_empty('001', '010'), False)
        self.assertEqual(self.tree.range_is_empty('001', '011'), False)
        self.assertEqual(self.tree.range_is_empty('001', '999'), False)
        
        self.assertEqual(self.tree.range_is_empty('002', '002'), False)
        self.assertEqual(self.tree.range_is_empty('002', '003'), False)
        self.assertEqual(self.tree.range_is_empty('002', '004'), False)
        self.assertEqual(self.tree.range_is_empty('002', '005'), False)
        self.assertEqual(self.tree.range_is_empty('002', '006'), False)
        self.assertEqual(self.tree.range_is_empty('002', '007'), False)
        self.assertEqual(self.tree.range_is_empty('002', '008'), False)
        self.assertEqual(self.tree.range_is_empty('002', '009'), False)
        self.assertEqual(self.tree.range_is_empty('002', '010'), False)
        self.assertEqual(self.tree.range_is_empty('002', '011'), False)
        self.assertEqual(self.tree.range_is_empty('002', '999'), False)
        
        self.assertEqual(self.tree.range_is_empty('003', '003'), True)
        self.assertEqual(self.tree.range_is_empty('003', '004'), False)
        self.assertEqual(self.tree.range_is_empty('003', '005'), False)
        self.assertEqual(self.tree.range_is_empty('003', '006'), False)
        self.assertEqual(self.tree.range_is_empty('003', '007'), False)
        self.assertEqual(self.tree.range_is_empty('003', '008'), False)
        self.assertEqual(self.tree.range_is_empty('003', '009'), False)
        self.assertEqual(self.tree.range_is_empty('003', '010'), False)
        self.assertEqual(self.tree.range_is_empty('003', '011'), False)
        self.assertEqual(self.tree.range_is_empty('003', '999'), False)
        
        self.assertEqual(self.tree.range_is_empty('004', '004'), False)
        self.assertEqual(self.tree.range_is_empty('004', '005'), False)
        self.assertEqual(self.tree.range_is_empty('004', '006'), False)
        self.assertEqual(self.tree.range_is_empty('004', '007'), False)
        self.assertEqual(self.tree.range_is_empty('004', '008'), False)
        self.assertEqual(self.tree.range_is_empty('004', '009'), False)
        self.assertEqual(self.tree.range_is_empty('004', '010'), False)
        self.assertEqual(self.tree.range_is_empty('004', '011'), False)
        self.assertEqual(self.tree.range_is_empty('004', '999'), False)
        
        self.assertEqual(self.tree.range_is_empty('005', '005'), True)
        self.assertEqual(self.tree.range_is_empty('005', '006'), False)
        self.assertEqual(self.tree.range_is_empty('005', '007'), False)
        self.assertEqual(self.tree.range_is_empty('005', '008'), False)
        self.assertEqual(self.tree.range_is_empty('005', '009'), False)
        self.assertEqual(self.tree.range_is_empty('005', '010'), False)
        self.assertEqual(self.tree.range_is_empty('005', '011'), False)
        self.assertEqual(self.tree.range_is_empty('005', '999'), False)
        
        self.assertEqual(self.tree.range_is_empty('006', '006'), False)
        self.assertEqual(self.tree.range_is_empty('006', '007'), False)
        self.assertEqual(self.tree.range_is_empty('006', '008'), False)
        self.assertEqual(self.tree.range_is_empty('006', '009'), False)
        self.assertEqual(self.tree.range_is_empty('006', '010'), False)
        self.assertEqual(self.tree.range_is_empty('006', '011'), False)
        self.assertEqual(self.tree.range_is_empty('006', '999'), False)
        
        self.assertEqual(self.tree.range_is_empty('007', '007'), True)
        self.assertEqual(self.tree.range_is_empty('007', '008'), False)
        self.assertEqual(self.tree.range_is_empty('007', '009'), False)
        self.assertEqual(self.tree.range_is_empty('007', '010'), False)
        self.assertEqual(self.tree.range_is_empty('007', '011'), False)
        self.assertEqual(self.tree.range_is_empty('007', '999'), False)
        
        self.assertEqual(self.tree.range_is_empty('008', '008'), False)
        self.assertEqual(self.tree.range_is_empty('008', '009'), False)
        self.assertEqual(self.tree.range_is_empty('008', '010'), False)
        self.assertEqual(self.tree.range_is_empty('008', '011'), False)
        self.assertEqual(self.tree.range_is_empty('008', '999'), False)
        
        self.assertEqual(self.tree.range_is_empty('009', '009'), True)
        self.assertEqual(self.tree.range_is_empty('009', '010'), False)
        self.assertEqual(self.tree.range_is_empty('009', '011'), False)
        self.assertEqual(self.tree.range_is_empty('009', '999'), False)
        
        self.assertEqual(self.tree.range_is_empty('010', '010'), False)
        self.assertEqual(self.tree.range_is_empty('010', '011'), False)
        self.assertEqual(self.tree.range_is_empty('010', '999'), False)
        
        self.assertEqual(self.tree.range_is_empty('011', '011'), True)
        self.assertEqual(self.tree.range_is_empty('011', '999'), True)
        
        self.assertEqual(self.tree.range_is_empty('999', '999'), True)

    def test_remove_range_removes_everything(self):
        for key in ['%03d' % i for i in range(1000)]:
            self.tree.insert(key, key)
        self.tree.remove_range('000', '999')
        self.assertEqual(self.tree.lookup_range('000', '999'), [])

    def test_remove_range_removes_single_key_in_middle(self):
        self.create_tree_for_range()
        self.tree.remove_range('004', '004')
        self.assertEqual(self.tree.lookup_range('000', '999'), 
                          [('002', '002'), 
                           ('006', '006'),
                           ('008', '008')])

    def test_remove_range_removes_from_beginning_of_keys(self):
        self.create_tree_for_range()
        self.tree.remove_range('000', '004')
        self.assertEqual(self.tree.lookup_range('000', '999'), 
                          [('006', '006'),
                           ('008', '008')])

    def test_remove_range_removes_from_middle_of_keys(self):
        self.create_tree_for_range()
        self.tree.remove_range('003', '007')
        self.assertEqual(self.tree.lookup_range('000', '999'), 
                          [('002', '002'),
                           ('008', '008')])

    def test_remove_range_removes_from_end_of_keys(self):
        self.create_tree_for_range()
        self.tree.remove_range('007', '009')
        self.assertEqual(self.tree.lookup_range('000', '999'), 
                          [('002', '002'), 
                           ('004', '004'),
                           ('006', '006')])

    def test_remove_range_removes_from_empty_tree(self):
        self.create_tree_for_range()
        self.tree.remove_range('000', '999')
        self.tree.remove_range('007', '009')
        self.assertEqual(self.tree.lookup_range('000', '999'), [])

    def test_bug_remove_range_when_only_key_is_larger_than_maxkey(self):
        self.tree.insert('555', '555')
        self.tree.remove_range('000', '111')
        self.assertEqual(self.tree.lookup_range('000', '999'), 
                         [('555', '555')])
 
    def test_removes_range_from_leaf(self):
        leaf = btree.LeafNode(0, 
                              [('000', '000'), ('111', '111'), ('222', '222')])
        new = self.tree._remove_range_from_leaf(leaf, '111', '222')
        self.assertEqual(new.pairs(), [('000', '000')])


class BTreeDecrementTests(unittest.TestCase):

    def setUp(self):
        # We use a small node size so that all code paths are traversed
        # during testing. Use coverage.py to make sure they do.
        self.codec = btree.NodeCodec(3)
        self.ns = DummyNodeStore(64, self.codec)
        self.forest = DummyForest()
        self.tree = btree.BTree(self.forest, self.ns, None)
        self.tree.insert('foo', 'bar')
        
    def test_store_has_two_nodes(self):
        self.assertEqual(len(self.ns.find_nodes()), 2)
        
    def test_initially_everything_has_refcount_1(self):
        for node_id in self.ns.find_nodes():
            self.assertEqual(self.ns.get_refcount(node_id), 1)

    def test_decrement_removes_everything(self):
        self.tree.decrement(self.tree.root.id)
        self.assertEqual(len(self.ns.find_nodes()), 0)

    def test_decrement_does_not_remove_anything(self):
        self.ns.set_refcount(self.tree.root.id, 2)
        self.tree.decrement(self.tree.root.id)
        self.assertEqual(len(self.ns.find_nodes()), 2)


class BTreeBalanceTests(unittest.TestCase):

    def setUp(self):
        ns = DummyNodeStore(4096, btree.NodeCodec(2))
        forest = DummyForest()
        self.tree = btree.BTree(forest, ns, None)
        self.keys = ['%02d' % i for i in range(10)]
        self.depth = None

    def leaves_at_same_depth(self, node, depth=0):
        if isinstance(node, btree.LeafNode):
            if self.depth is None:
                self.depth = depth
            return self.depth == depth
        else:
            assert isinstance(node, btree.IndexNode)
            for key in node:
                child = self.tree.get_node(node[key])
                if not self.leaves_at_same_depth(child, depth + 1):
                    return False
            return True
            
    def indexes_filled_right_amount(self, node, isroot=True):
        if isinstance(node, btree.IndexNode):
            if not isroot:
                if len(node) < self.fanout or len(node) > 2 * self.fanout + 1:
                    return False
            for key in node:
                child = self.tree.get_node(node[key])
                ok = self.indexes_filled_right_amount(child, isroot=False)
                if not ok:
                    return False
        return True

    def test_insert_puts_every_leaf_at_same_depth(self):
        for key in self.keys:
            self.tree.insert(key, key)
            self.depth = None
            self.assert_(self.leaves_at_same_depth(self.tree.root),
                         'key#%d failed' % (self.keys.index(key) + 1))
        
    def test_insert_fills_every_index_node_the_right_amount(self):
        self.assert_(self.indexes_filled_right_amount(self.tree.root))
        for key in self.keys:
            self.tree.insert(key, key)
            self.assert_(self.indexes_filled_right_amount(self.tree.root))
            
    def test_remove_keeps_every_leaf_at_same_depth(self):
        for key in self.keys:
            self.tree.insert(key, key)
        for key in self.keys:
            self.tree.remove(key)
            self.assert_(self.leaves_at_same_depth(self.tree.root))

