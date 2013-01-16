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
import nodestore_memory


class NodeStoreMemoryTests(unittest.TestCase, larch.NodeStoreTests):

    def setUp(self):
        self.node_size = 4096
        self.codec = larch.NodeCodec(self.key_bytes)
        self.ns = nodestore_memory.NodeStoreMemory(allow_writes=True, node_size=self.node_size, codec=self.codec)

