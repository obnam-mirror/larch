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


from distutils.core import setup

import larch

setup(
    name='larch',
    version=larch.version,
    description='copy-on-write B-tree data structure',
    long_description='''\
An implementation of a particular kind of B-tree, based on research
by Ohad Rodeh. This is the same data structure that btrfs uses, but
in a new, pure-Python implementation.

The distinctive feature of this B-tree is that a node is never (conceptually)
modified. Instead, all updates are done by copy-on-write. This makes it
easy to clone a tree, and modify only the clone, while other processes
access the original tree.

The implementation is generic and flexible, so that you may use it in
a variety of situations. For example, the tree itself does not decide
where its nodes are stored: you provide a class that does that for it.
The library contains two implementations, one for in-memory and one
for on-disk storage.
''',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Topic :: Software Development :: Libraries',
    ],
    author='Lars Wirzenius',
    author_email='liw@liw.fi',
    url='http://liw.fi/larch/',
    packages=['larch'],
)

