Block User Space Filesystem
=============================

What does it do?
-----------------

Provides read/write access to one large file of a specified length. The file is
backed by a folder, in which the 4MB sized blocks it consists of are stored.

The blocks are compressed transparently, and encrypted.

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

Encryption / compression details
----------------------------------
 * Content is compressed before storage. zlib is used 
   (you can use `zlib-flate -uncompress` to access the data)
 * When a password is specified, AES CBC is used from pycrypto. The IV is set to 
   the block number. This constitutes symmetric encryption.
 * GPG was considered, but requires you to still have access to your secret gpg 
   file -- which may not be true for backups.



