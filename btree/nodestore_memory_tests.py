import unittest

import btree
import nodestore_memory


class NodeStoreMemoryTests(unittest.TestCase, btree.NodeStoreTests):

    def setUp(self):
        self.node_size = 4096
        self.ns = nodestore_memory.NodeStoreMemory(self.node_size)

