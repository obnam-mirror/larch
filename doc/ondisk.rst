On-disk file format and data structure
======================================

Larch B-tree forests are stored on the disk as follows:

* Each forest is stored in a separate directory tree structure.
* The file ``metadata`` is in the INI format, and stores metadata about
  the forest, including the identifiers of the root nodes of the trees.
* The ``nodes`` directory contains the actual nodes.
* The ``refcounts`` directory contains reference counts for nodes.

The metadata file
-----------------

The following values are stored in the metadata file:

* ``format`` is ``1/1``: node store format version 1 and node codec version 1.
* ``node_size`` is the maximum size of an encoded node, in bytes.
* ``key_size`` is the size of the keys, in bytes.
* ``last_id`` is the latest allocated node identifier in the forest.
* ``root_ids`` lists the identifiers of the root nodes of the trees.

Node files
----------

Leaf nodes are encoded as follows:

* the first four bytes are 'O', 'R', 'B', 'L'
* 64-bit unsigned integer giving the node identifier
* 32-bit unsigned integer giving the number of key/value pairs
* all keys catenated
* lengths of values as 32-bit unsigned integers
* all values catenated

Index nodes are encoded as follows:

* the first four bytes are 'O', 'R', 'B', 'I'
* 64-bit unsigned integer giving the node identifier
* 32-bit integer giving the number of keys
* all keys catenated
* all child ids catenated, where each id is a 64-bit unsigned integer

All integers are in big-endian order.

All root nodes are index nodes, so decoding can start knowing that
the first node is an index node.

Each node is stored in a file under the ``nodes`` subdirectory,
using multiple levels of directories to avoid having too many files
in the same directory. The basename of the file is the node identifier
in hexadecimal.

The directory levels are user adjustable, see the ``IdPath`` class
for details.

Reference counts
----------------

Each node has a reference count. When the count drops to zero, the
node file gets removed. Reference counts are stored in files under
the ``refcounts`` subdirectory. Each file there contains up to 
32768 reference counts, as a 16-bit unsigned big-endian integer.
Thus, the reference count for node i is file named ``refcount-N``
where N is i modulo 32768.

A refcount file that is full of zeroes is removed. When looking up
refcounts, if the file does not exist, the count is assumed to be zero.
This avoids having to store refcounts for deleted nodes indefinitely.

