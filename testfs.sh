echo ===============
echo "testing filesystem on blockfs"
mkdir -p p1 || exit 1
/sbin/mkfs.ext2 test/block || exit 1
echo "  mounting"
sudo mount -t ext2 -o loop test/block p1/ || exit 1
echo "  writing"
echo "my secret content foo goes into /bar" > p1/bar || exit 1
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

