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


import os
import sys

import shutil
import tempfile
import unittest

import larch
import larch.fsck
import StringIO
import ttystatus

class FsckTests(unittest.TestCase):
    KEY_SIZE        =  15
    NODE_SIZE       = 128 
    VALUES_SIZE     =   7
    NB_KEYS         =  40
    def setUp(self):
        self.logged_errors   = []
        self.logged_warnings = []
        self.dirname         = tempfile.mkdtemp()
        self.forest          = self.new_disk_forest()

    def tearDown(self):
        self.logged_errors   = []
        self.logged_warnings = []
        shutil.rmtree(self.dirname)

    def log_warning(self, msg):
        self.logged_warnings.append(msg)

    def log_error(self, msg):
        self.logged_errors.append(msg)

    def new_disk_forest(self):
        forest = larch.open_forest(
                    allow_writes=True, 
                    key_size=self.KEY_SIZE, node_size=self.NODE_SIZE,
                    dirname=self.dirname, node_store=larch.NodeStoreDisk)
        t1=forest.new_tree()
        for i in xrange(self.NB_KEYS):
            value='%0*d' % (self.VALUES_SIZE, 1*i)
            key  ='%0*d' % (self.KEY_SIZE, 1*i)
            t1.insert(key,value)
        forest.commit()
        return forest

    def get_any_node(self, index_node=False):
        """returns either index node or leaf node"""
        any_node=None
        for x in xrange(10,self.forest.last_id):
            node = self.forest.node_store.get_node(x)
            if index_node and isinstance(node, larch.IndexNode):
                any_node = node
                break
            elif (not index_node) and isinstance(node, larch.LeafNode):
                any_node = node
                break
        self.failUnless(any_node is not None)
        return any_node

    def testError(self):
        e = larch.fsck.Error('test')

    def testWorkItem(self):
        wi = larch.fsck.WorkItem()
        self.failUnless( 'WorkItem' == str(wi) )
        wi.name = "SomeName"
        self.failUnless( 'SomeName' == str(wi) )
        wi.do() # does nothing :)
        wi.fsck = larch.fsck.Fsck(self.forest, warning=self.log_warning, error=self.log_error, fix=False)
        self.failIf( self.logged_warnings )
        wi.warning('Glip')
        self.failUnless( 'Glip' in self.logged_warnings[0] )
        self.failIf( self.logged_errors )
        wi.error('Plop')
        self.failUnless( 'Plop' in self.logged_errors[0] )
        node = self.get_any_node()
        node_id = node.id
        wi.start_modification(node)
        wi.put_node(node)
        newnode = self.forest.node_store.get_node(node.id)
        self.failUnless( node == newnode )


    def test_CheckIndexNode(self):
        Ffsck =  larch.fsck.Fsck(self.forest, warning=self.log_warning, error=self.log_error, fix=False)
        cin = larch.fsck.CheckIndexNode(Ffsck, self.get_any_node(index_node=True) )
        for work in cin.do():
            work.do() # No error expected
        self.failIf( self.logged_warnings )
        self.failIf( self.logged_errors )
        # Give a leaf node instead of an index node:
        cin2 = larch.fsck.CheckIndexNode(Ffsck, self.get_any_node(index_node=False) )
        for work in cin2.do():
            work.do() # error expected
        self.failIf( self.logged_warnings )
        self.failUnless('Expected to get an index node' in self.logged_errors[0] )
        self.failUnless("got <class 'larch.nodes.LeafNode'> instead" in self.logged_errors[0], self.logged_errors[0] )
        

    def test_CheckIndexNodeNoChildren(self):
        Ffsck =  larch.fsck.Fsck(self.forest, warning=self.log_warning, error=self.log_error, fix=False)
        # Create an index node without children:
        index_node = self.get_any_node(index_node=True)
        empty_node = larch.IndexNode(index_node.id, [], [])
        cin = larch.fsck.CheckIndexNode(Ffsck, empty_node )
        for work in cin.do():
            work.do() # Expect "No children" error
        self.failIf( self.logged_warnings )
        self.failUnless('index node %d: No children' % empty_node.id in self.logged_errors[0], self.logged_errors[0] )


    def test_CheckIndexNodeFixReferences(self):
        # Create an index node with a missing reference:
        index_node_missing_reference = self.get_any_node(index_node=True)
        id_index_node = index_node_missing_reference.id
        id_node_to_remove = index_node_missing_reference.values()[0]
        mkey = index_node_missing_reference.keys()[0]
        # Let's remove the node_to_remove from the FS:
        nodepath = self.forest.node_store.idpath.convert(id_node_to_remove)
        os.unlink( nodepath )
        del self.forest
        Fforest = larch.open_forest(allow_writes=False,dirname=self.dirname)
        Ffsck  =  larch.fsck.Fsck(Fforest, warning=self.log_warning, error=self.log_error, fix=True)
        index_node_missing_reference = Fforest.node_store.get_node(id_index_node)
        cin = larch.fsck.CheckIndexNode(Ffsck, index_node_missing_reference )
        for work in cin.do():
           work.do() # Expect dropped keys path
        self.failUnless(
            'index node %s: dropped key %s' %
            (id_index_node, mkey.encode('hex')) in self.logged_warnings[0],
            self.logged_warnings[0] )
        # We have a "node %d is missing" error as well:
        self.failUnless( 'node %s is missing' % id_node_to_remove in  self.logged_errors[0], self.logged_errors[0] )


    def test_CheckRefcounts(self):
        Fforest = larch.open_forest(allow_writes=True,dirname=self.dirname)
        Ffsck   = larch.fsck.Fsck(Fforest,
                                  warning=self.log_warning, error=self.log_error,
                                  fix = False)
        # Populate self.refcounts
        Ffsck.run_fsck()
        self.failIf( self.logged_warnings )
        self.failIf( self.logged_errors )
        leafnode = self.get_any_node()
        self.failUnless( Ffsck.refcounts[leafnode.id] == 1 , Ffsck.refcounts[leafnode.id] )
        # Change a refcount so that it is bad:
        Ffsck2  = larch.fsck.Fsck(Fforest,
                                  warning=self.log_warning, error=self.log_error,
                                  fix = False)
        self.failUnless( 1 == Fforest.node_store.rs.get_refcount(leafnode.id) )
        Fforest.node_store.rs.set_refcount(leafnode.id,2)
        Fforest.node_store.rs.save_refcounts()
        Fforest.commit()
        # Check the refcounts
        Ffsck2.run_fsck()
        self.failIf( self.logged_warnings )
        self.failUnless( 'node %s: refcount is %s but should be %s' % (leafnode.id, 2,1) in self.logged_errors[0], self.logged_errors[0] )
        self.failUnless( 2 == Fforest.node_store.rs.get_refcount(leafnode.id) )
        # Fix the refcounts:
        self.logged_errors   = []
        self.logged_warnings = []
        Ffsck3  = larch.fsck.Fsck(Fforest,
                                  warning=self.log_warning, error=self.log_error,
                                  fix = True)
        Ffsck3.run_fsck()
        self.failUnless( 'node %s: refcount is %s but should be %s' % (leafnode.id, 2,1) in self.logged_errors[0], self.logged_errors[0] )
        self.failUnless( 'node %s: refcount was set to %s' % (leafnode.id, 1) in self.logged_warnings[0], self.logged_warnings[0] )
        self.failUnless( 1 == Fforest.node_store.rs.get_refcount(leafnode.id) )
        # No more errors expected:
        self.logged_errors   = []
        self.logged_warnings = []
        Ffsck4  = larch.fsck.Fsck(Fforest,
                                  warning=self.log_warning, error=self.log_error,
                                  fix = True)
        Ffsck4.run_fsck()
        self.failIf( self.logged_warnings )
        self.failIf( self.logged_errors )



    def test_missing_leaf_node(self):
        # Let's delete a leaf node
        leafnode = self.get_any_node()
        self.failUnless(leafnode is not None)
        # delete the node:
        nodepath = self.forest.node_store.idpath.convert(leafnode.id)
        os.unlink( nodepath )
        # fsck the forest
        Fforest = larch.open_forest(allow_writes=False,dirname=self.dirname)
        Ffsck    = larch.fsck.Fsck(Fforest, 
                    warning=self.log_warning, error=self.log_error,
                    fix = False)
        Ffsck.run_fsck()
        # Make sure that the missing node is noticed
        self.failUnless( True in [ 'node %d is missing' % leafnode.id in x for x in self.logged_errors ] )

    def test_missing_index_node(self):
        # Let's delete a index node
        indexnode = self.get_any_node(index_node=True)
        self.failUnless(indexnode is not None)
        # delete the node:
        nodepath = self.forest.node_store.idpath.convert(indexnode.id)
        os.unlink( nodepath )
        # fsck the forest
        Fforest = larch.open_forest(allow_writes=False,dirname=self.dirname)
        Ffsck    = larch.fsck.Fsck(Fforest, 
                    warning=self.log_warning, error=self.log_error,
                    fix = False)
        Ffsck.run_fsck()
        # Make sure that the missing node is noticed
        self.failUnless( True in [ 'node %d is missing' % indexnode.id in x for x in self.logged_errors ] )


    def test_fsck(self):
        Fforest = larch.open_forest(allow_writes=False,dirname=self.dirname)
        Ffsck   = larch.fsck.Fsck(Fforest,
                                  warning=self.log_warning, error=self.log_error,
                                  fix = False)
        # Run fsck
        ts = ttystatus.TerminalStatus()
        Ffsck.run_fsck(ts=ts)
        self.failIf( self.logged_warnings )
        self.failIf( self.logged_errors )
 


#Start the tests     
if __name__ == '__main__':
    unittest.main()

