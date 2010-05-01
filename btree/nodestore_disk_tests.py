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

