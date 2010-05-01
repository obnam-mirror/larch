import shutil
import tempfile
import unittest

import btree
import nodestore_disk


class NodeStoreDiskTests(unittest.TestCase, btree.NodeStoreTests):

    def setUp(self):
        self.node_size = 4096
        self.codec = btree.NodeCodec(self.key_bytes)
        self.tempdir = tempfile.mkdtemp()
        self.ns = nodestore_disk.NodeStoreDisk(self.tempdir, self.node_size,
                                               self.codec)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_has_persistent_metadata(self):
        self.ns.set_metadata('foo', 'bar')
        self.ns.save_metadata()
        ns2 = nodestore_disk.NodeStoreDisk(self.tempdir, self.node_size, 
                                           self.codec)
        self.assertEqual(ns2.get_metadata('foo'), 'bar')

    def test_metadata_does_not_persist_without_saving(self):
        self.ns.set_metadata('foo', 'bar')
        ns2 = nodestore_disk.NodeStoreDisk(self.tempdir, self.node_size, 
                                           self.codec)
        self.assertEqual(ns2.get_metadata_keys(), [])

