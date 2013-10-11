> blockfs-debug.log
dd if=/dev/urandom of=testcontent_1 bs=1k count=100 || exit 1
dd if=/dev/urandom of=testcontent_2 bs=1M count=10 || exit 1
dd if=/dev/urandom of=testcontent_3 bs=1k count=100 || exit 1

dd if=testcontent_1 of=test/block bs=1k count=100 conv=notrunc || exit 1
rm -f testcontent_1_out
dd of=testcontent_1_out if=test/block bs=1k count=100 || exit 1
echo "checking input/output of 100kB block"
cmp --verbose testcontent_1 testcontent_1_out | head || exit 1
> blockfs-debug.log
echo ===============

dd if=testcontent_2 of=test/block bs=1M count=10 conv=notrunc || exit 1
rm -f testcontent_2_out
dd of=testcontent_2_out if=test/block bs=1M count=10 || exit 1
echo "checking input/output of 10MB block"
du -sb testcontent_2 testcontent_2_out
cmp testcontent_2 testcontent_2_out || exit 1
> blockfs-debug.log
echo ===============

dd of=testcontent_2_out if=/dev/zero bs=1k count=100 seek=4000 conv=notrunc || exit 1
dd of=testcontent_2_out if=test/block bs=1k count=100 seek=4000 skip=4000 conv=notrunc || exit 1
echo "checking read of sub-block block"
du -sb testcontent_2 testcontent_2_out
cmp testcontent_2 testcontent_2_out || exit 1
> blockfs-debug.log

echo ===============
dd if=testcontent_3 of=testcontent_2 bs=1k count=100 seek=4000 conv=notrunc || exit 1
dd if=testcontent_3 of=test/block bs=1k count=100 seek=4000 conv=notrunc || exit 1
rm -f testcontent_3_out
echo "checking rewrite of 1kB chunk somewhere in the middle"
dd of=testcontent_3_out if=test/block  bs=1k count=100 skip=4000 || exit 1
du -sb testcontent_3 testcontent_3_out
cmp testcontent_3 testcontent_3_out || exit 1
> blockfs-debug.log
echo ===============
rm -f testcontent_3_out
dd of=testcontent_3_out if=test/block bs=1M count=10 || exit 1
echo "checking rewrite of 1kB chunk somewhere in the middle -- reading whole"
cmp testcontent_2 testcontent_3_out || exit 1
> blockfs-debug.log

echo ===============
echo "testing filesystem on blockfs"
mkdir -p p1 || exit 1
/sbin/mkfs.ext2 test/block || exit 1
echo "  mounting"
sudo mount -t ext2 -o loop test/block p1/ || exit 1
echo "  writing"
echo foo > p1/bar || exit 1
sync
sleep 1
echo "  unmounting"
sudo umount p1/ || exit 1
echo "  mounting"
sudo mount -t ext2 -o loop test/block p1/ || exit 1
echo "  reading"
cat p1/bar || exit 1
sync
sleep 1
echo "  unmounting"
sudo umount p1/ || exit 1
echo ===============

echo TEST SUCCESSFUL

