#!/usr/bin/python
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


import sys

import btree


def main():
    dirname = sys.argv[1]
    node_size = int(sys.argv[2])
    key_size = int(sys.argv[3])

    codec = btree.NodeCodec(key_size)
    ns = btree.NodeStoreDisk(dirname, node_size, codec)
    
    keys = ns.get_metadata_keys()
    print 'ns metadata keys:', keys


if __name__ == '__main__':
    main()
