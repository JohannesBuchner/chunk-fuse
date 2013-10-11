#!/usr/bin/env python

from __future__ import with_statement

from errno import EACCES, ENOENT
from stat import S_IFDIR, S_IFLNK, S_IFREG
from threading import Lock
from time import time
from ctypes import create_string_buffer

import os, os.path, sys


from fuse import FUSE, FuseOSError, Operations, LoggingMixIn

def forbidden(*args, **kwargs):
	raise FuseOSError(EACCES)
def empty(*args, **kwargs):
	return {}

#import zlib
import gzip
CHUNKSIZE = (1024 * 1024 * 4)

class Block(LoggingMixIn, Operations):
	"""
	Provides a large data block. In the backing directory, 4MB blocks of
	compressed, encrypted data are stored.
	"""
	def __init__(self, root, nchunks):
		self.root = os.path.realpath(root)
		self.rwlock = Lock()
		self.fd = 0
		self.cache = {}
		self.nchunks = nchunks
		now = time()
		self.fileprops = dict(st_mode=(S_IFREG | 0755), st_nlink=1,
                                st_size=nchunks * CHUNKSIZE, 
                                st_blocks=nchunks * CHUNKSIZE / 512, #st_blksize=CHUNKSIZE,
                                st_ctime=now, st_mtime=now, st_atime=now)
		self.rootprops = dict(st_mode=(S_IFDIR | 0755), st_ctime=now, 
			st_mtime=now, st_atime=now, st_nlink=2)

	def access(self, path, mode):
		if not os.access(self.root, mode):
			raise FuseOSError(EACCES)

	chmod = forbidden
	chown = forbidden
	create = forbidden
	getattr = empty
	link = forbidden
	mkdir = forbidden
	mknod = forbidden
	getxattr = None
	listxattr = None
	
	link = forbidden
	readlink = forbidden
	
	def flush(self, path, fh):
		return self._flush()

	def destroy(self, path):
		return self._flush(force_write=True)

	def fsync(self, path, datasync, fh):
		return self._flush()

	def getattr(self, path, fh=None):
		if path == '/':
			return self.rootprops
		elif path == '/block':
			return self.fileprops
		else:
			raise FuseOSError(ENOENT)

	def readdir(self, path, fh):
		return ['.', '..', 'block']
	
	def open(self, path, flags):
		self.fd += 1
		return self.fd
	
	def cached_chunk(self, i):
		if i not in self.cache:
			path = os.path.join(self.root, '%d.gz' % i)
			if not os.path.exists(path): # create
				self.log.debug('creating as empty')
				#buf = bytearray(CHUNKSIZE)
				buf = b'\0' * CHUNKSIZE
				self.cache[i] = dict(data=buf, t_write=time(), t_read=time(), dirty=True)
			else: # load
				self.log.debug('loading chunk %d into cache' % i)
				f = gzip.open(path, 'rb')
				buf = f.read()
				f.close()
				self.cache[i] = dict(data=buf, t_write=time(), t_read=time(), dirty=False)
		self.cache[i]['t_read'] = time()
		
		self.log.debug('chunk %d: %s' % (i, 
			dict(t_read=self.cache[i]['t_read'], 
				t_write=self.cache[i]['t_write'], 
				dirty=self.cache[i]['dirty'])) )
		return self.cache[i]
	
	def writeblock(self, i):
		self.log.debug('writing chunk %d onto fs' % i)
		#data = zlib.compress(self.cache[i]['data'])
		path = os.path.join(self.root, '%d.gz' % i)
		f = gzip.open(path, 'wb')
		f.write(self.cache[i]['data'])
		#f = file(path, 'wb')
		#f.write(data)
		f.flush()
		os.fsync(f.fileno())
		f.close()
		self.cache[i]['dirty'] = False
		self.log.debug('writing chunk %d done' % i)
		return 0
	
	def _flush(self, force_write=False):
		with self.rwlock:
			self.log.debug('flushing...')
			to_remove = []
			for i, props in self.cache.iteritems():
				self.log.debug('flushing: %d is %.1fs/%.1fs old' % (i, time() - props['t_write'], time() - props['t_write']))
				if time() - props['t_read'] > 10:
					self.log.debug('flushing: %d stale' % i)
					if len(self.cache) > 10:
						to_remove.append(i)
				if (force_write or time() - props['t_write'] > 3) and props['dirty']:
					self.log.info('flushing: %d dirty' % i)
					r = self.writeblock(i)
					if r != 0:
						self.log.debug('flushing: %d writing failed' % i)
						return r
			for i in to_remove:
				del self.cache[i]
				self.log.debug('flushing: %d removed' % i)
		self.log.debug('flushing finished')
		return 0
	
	def getblock(self, offset, size):
		self.log.debug('getblock getting data from %d %d' % (offset, size))
		data = b''
		# merge into contiguous
		for i in range(offset / CHUNKSIZE, (offset + size) / CHUNKSIZE + 1):
			data += self.cached_chunk(i)['data']
		# get right part
		begin = offset % CHUNKSIZE
		r =  data[begin:begin + size]
		self.log.debug('getblock %d %d done; returning %d bytes' % (offset, size, len(r)))
		return r
	
	def createblocks(self, offset, data):
		size = len(data)
		self.log.debug('creating block %d %d' % (offset, size))
		begin = offset % CHUNKSIZE
		databegin = 0
		sizeleft = size
		
		for i in range(offset / CHUNKSIZE, (offset + size) / CHUNKSIZE + 1):
			chunk = self.cached_chunk(i)
			length = min(CHUNKSIZE - begin, sizeleft)
			# take from data[databegin:databegin + length]
			# write to begin:min(begin + size, CHUNKSIZE)
			
			if chunk['data'][begin:begin + length] != data[databegin:databegin + length]:
				self.log.debug('modifying block %d: chunk %d : %d <- data %d : %d' % (i, begin, begin + length, databegin, databegin + length))
				chunk['age'] = time()
				chunk['dirty'] = True
				chunk['data'] = chunk['data'][0:begin] + \
					data[databegin:databegin + length] + \
					chunk['data'][begin+length:]
				# chunk['data'][begin:begin + length] = data[databegin:databegin + length]
			
			databegin += length
			sizeleft -= length
			begin = 0
			
		self.log.debug('creating block %d %d done' % (offset, size))
		return size
	
	def read(self, path, size, offset, fh):
		self.log.debug('read of %s @%d %d' % (path, offset, size))
		with self.rwlock:
			return self.getblock(offset, size)
		self.log.error('read of %s @%d %d failed!' % (path, offset, size))
		raise FuseOSError(EROFS)
	
	def write(self, path, data, offset, fh):
		with self.rwlock:
			return self.createblocks(offset, data)
		raise FuseOSError(EROFS)

	#def release(self, path, fh):
	#	return 0

	rename = forbidden
	rmdir = forbidden
	symlink = forbidden
	unlink = forbidden
	utimens = forbidden
	
	def statfs(self, path):
		self.log.debug('statfs')
		return dict(f_bsize=CHUNKSIZE, f_blocks=self.nchunks, f_bavail=0)
		
	def truncate(self, path, length, fh=None):
		raise FuseOSError(EROFS)
		self.log.debug('truncate :/')
		with self.rwlock:
			# set rest of last block to 0
			i = length / CHUNKSIZE
			self.createblocks(length, b'\0' * (CHUNKSIZE - length % CHUNKSIZE))
			# remove other blocks
			for j in range(i + 1, self.nchunks):
				path = os.path.join(self.root, '%d.gz' % j)
				if j in self.cache:
					del self.cache[j]
				if os.path.exists(path):
					os.unlink(path)

if __name__ == '__main__':
	if len(sys.argv) != 4:
		print('usage: %s <folder> <nchunks> <mountpoint>' % sys.argv[0])
		sys.exit(1)
	
	import logging
	logging.basicConfig(filename='blockfs-debug.log',level=logging.INFO)
	b = Block(sys.argv[1], int(sys.argv[2]))
	fuse = FUSE(b, sys.argv[3], nothreads=True, foreground=True,
		allow_root=True)
	

