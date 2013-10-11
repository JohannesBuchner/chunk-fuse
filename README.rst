Block User Space Filesystem
=============================

What does it do?
-----------------

Provides read/write access to one large file of a specified length. The file is
backed by a folder, in which the 4MB sized blocks it consists of are stored.

The blocks are compressed transparently. In future, encryption may be added.

What is the point?
-------------------

You may have cloud FUSE file systems, which give you folders to store data in.
If you do not want the service to have access to the data, you want to encrypt it.
So use this block to create a file system backed by the cloud.

Going further, if you have multiple cloud file systems, you can merge them
using lvm across the blocks, which will give you a RAID-like system.

 * Access to multiple remote systems
 * Redundant
 * Encrypted -- data is safe from cloud operators
 * Compressed
 * fully native POSIX filesystem of your choice (reiserfs, ext4, etc.)

As a sketch::

  Cloud service 
     |
  FUSE CloudFS: local folder 
     |
  BlockFS (this project): file
     |
  loop mount file as block, using normal file system (reiserfs, ext4); prepare with mkfs.*
  or: use file as lvm block


