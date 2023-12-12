#!/bin/bash
# doesn't actually fully work yet...
set -e
if [[ "$(id -u)" != 0 ]]; then
    exec sudo bash "$0" "$@"
fi
build_dir="$(mktemp -d)"
iso_dir="$build_dir/iso"
mounts=()
function at_exit() {
    set +e
    for i in "${mounts[@]}"; do
        umount "$i"
    done
    rm -rf --one-file-system "$build_dir"
}
trap at_exit EXIT
mmdebstrap -v --variant=apt --include=grub-ieee1275-bin,xorriso,gdbserver,linux-image-powerpc64le --architecture=ppc64el bullseye "$build_dir"
echo "gdb-vm-build" > "$build_dir"/etc/debian_chroot
if [[ "$(arch)" != "ppc64le" ]]; then
    cp /usr/bin/qemu-ppc64le-static "$build_dir"/usr/bin/qemu-ppc64le-static
fi
cp /etc/resolv.conf "$build_dir"/etc/resolv.conf
mount --bind /dev "$build_dir"/dev
mounts=("$build_dir"/dev "${mounts[@]}")
mount --bind /dev/pts "$build_dir"/dev/pts
mounts=("$build_dir"/dev/pts "${mounts[@]}")
mount --bind /proc "$build_dir"/proc
mounts=("$build_dir"/proc "${mounts[@]}")
mount --bind /sys "$build_dir"/sys
mounts=("$build_dir"/sys "${mounts[@]}")
mkdir "$iso_dir"
cat > "$build_dir"/etc/initramfs-tools/hooks/gdbserver <<'EOF'
#!/bin/sh

PREREQ=""
prereqs()
{
    echo "$PREREQ"
}

case $1 in
prereqs)
    prereqs
    exit 0
    ;;
esac

. /usr/share/initramfs-tools/hook-functions

echo copying gdbserver...
copy_exec /usr/bin/gdbserver /usr/bin/gdbserver

exit 0
EOF
chmod +x "$build_dir"/etc/initramfs-tools/hooks/gdbserver
cat > "$build_dir"/etc/initramfs-tools/scripts/init-top/gdbserver <<'EOF'
#!/bin/sh
PREREQ=""

prereqs()
{
    echo "$PREREQ"
}

case $1 in
# get pre-requisites
prereqs)
    prereqs
    exit 0
    ;;
esac

# TODO: call gdbserver on serial port instead...then poweroff
sh <>/dev/tty1 >&0 2>&0

exit 0
EOF
chmod +x "$build_dir"/etc/initramfs-tools/scripts/init-top/gdbserver
chroot "$build_dir" update-initramfs -k all -u
cp "$build_dir"/boot/vmlinu?-* "$iso_dir"/vmlinux
cp "$build_dir"/boot/initrd.img-* "$iso_dir"/initrd.gz
mkdir -p "$iso_dir"/boot/grub
cat > "$iso_dir"/boot/grub/grub.cfg <<'EOF'
set timeout=0
set default=0

menuentry "boot" {
    insmod gzio
    # not a real UUID, just makes initrd work...
    set root=(ieee1275/cdrom,apple3)
    linux /vmlinux root=UUID=2942fbed-5e30-4bbd-b1ba-5ac1875bc41c debug
    initrd /initrd.gz
}
EOF
chroot "$build_dir" grub-mkrescue -o gdb-vm.iso /iso
install -m 644 "$build_dir"/gdb-vm.iso gdb-vm.iso

