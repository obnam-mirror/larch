Welcome to larch's documentation!
=================================

This is an implementation of particular kind of B-tree, based on research by 
Ohad Rodeh. See "B-trees, Shadowing, and Clones" (link below) for details on 
the data structure. This is the same data structure that btrfs uses. 

The distinctive feature of these B-trees is that a node is 
never modified. Instead, all updates are done by copy-on-write. Among other 
things, this makes it easy to clone a tree, and modify only the clone, while 
other processes access the original tree. This is utterly wonderful for my 
backup application, and that's the reason I wrote larch in the first place.

I have tried to keep the implementation generic and flexibile, so that you 
may use it in a variety of situations. For example, the tree itself does not 
decide where its nodes are stored: you provide a class that does that for it. 
I have two implementations of the NodeStore class, one for in-memory and one 
for on-disk storage.

* Homepage: http://liw.fi/larch/
* Rodeh paper: http://liw.fi/larch/ohad-btrees-shadowing-clones.pdf


Quick start
===========

A **forest** is a collection of related **trees**: cloning a tree is
only possible within a forest. Thus, also, only trees in the same
forest can share nodes. All **keys** in a all trees in a forest
must be string of the same size. **Values** are strings and
are stored in **nodes**, and
can be of any size, almost up to half the size of a node.

When creating a forest, you must specify the sizes of keys and
nodes, and the directory in which everything gets stored::

    import larch

    key_size = 3
    node_size = 4096
    dirname = 'example.tree'

    forest = larch.open_forest(key_size=key_size, node_size=node_size,
                               dirname=dirname)

The above will create a new forest, if necessary, or open an existing
one (which must have been created using the same key and node sizes).

To create a new tree::

    tree = forest.new_tree()

Alternatively, to clone an existing tree if one exists::

    if forest.trees:
        tree = forest.new_tree(self.trees[-1])
    else:
        tree = forest.new_tree()

To insert some data into the tree::

    for key in ['abc', 'foo', bar']:
        tree.insert(key, key.upper())

To look up value for one key::

    print tree.lookup('foo')

To look up a range::

    for key, value in tree.lookup_range('aaa', 'zzz'):
        print key, value

To remove a key::

    tree.remove('abc')
    
To remove a range:

    tree.remove_range('aaa', 'zzz')

You probably don't need to worry about anything else than the
``Forest`` and ``BTree`` classes, unless you want to provide your
own ``NodeStore`` instance.

Reference manual
================

.. automodule:: larch
   :members:
   :undoc-members:


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

