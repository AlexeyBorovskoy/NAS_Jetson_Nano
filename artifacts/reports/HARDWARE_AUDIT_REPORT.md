# Hardware Audit Report

Generated: 2026-05-31T17:01:40+00:00

## uname
```
Linux nas_jetson_nano-jetson 4.9.253-tegra #1 SMP PREEMPT Sat Feb 19 08:59:22 PST 2022 aarch64 aarch64 aarch64 GNU/Linux
```
## os-release
```
NAME="Ubuntu"
VERSION="18.04.6 LTS (Bionic Beaver)"
ID=ubuntu
ID_LIKE=debian
PRETTY_NAME="Ubuntu 18.04.6 LTS"
VERSION_ID="18.04"
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
VERSION_CODENAME=bionic
UBUNTU_CODENAME=bionic
```
## RAM
```
              total        used        free      shared  buff/cache   available
Mem:           3.9G        396M        2.8G         50M        714M        3.3G
Swap:          1.9G          0B        1.9G
```
## Filesystems
```
Filesystem      Size  Used Avail Use% Mounted on
/dev/mmcblk0p1   60G   16G   42G  28% /
none            1.8G     0  1.8G   0% /dev
tmpfs           2.0G  4.0K  2.0G   1% /dev/shm
tmpfs           2.0G   30M  2.0G   2% /run
tmpfs           5.0M  4.0K  5.0M   1% /run/lock
tmpfs           2.0G     0  2.0G   0% /sys/fs/cgroup
/dev/sda1        15G  170M   14G   2% /mnt/storage
tmpfs           397M     0  397M   0% /run/user/1000
```
## Block devices
```
NAME           SIZE FSTYPE MOUNTPOINT   MODEL            SERIAL
loop0           16M vfat                                 
sda           14.5G                     USB DISK 2.0     070A8431B8588868
└─sda1        14.5G ext4   /mnt/storage                  
mtdblock0        4M                                      
mmcblk0       59.7G                                      0x9356673a
├─mmcblk0p1   59.7G ext4   /                             
├─mmcblk0p2    128K                                      
├─mmcblk0p3    448K                                      
├─mmcblk0p4    576K                                      
├─mmcblk0p5     64K                                      
├─mmcblk0p6    192K                                      
├─mmcblk0p7    384K                                      
├─mmcblk0p8     64K                                      
├─mmcblk0p9    448K                                      
├─mmcblk0p10   448K                                      
├─mmcblk0p11   768K                                      
├─mmcblk0p12    64K                                      
├─mmcblk0p13   192K                                      
└─mmcblk0p14   128K                                      
zram0        495.5M        [SWAP]                        
zram1        495.5M        [SWAP]                        
zram2        495.5M        [SWAP]                        
zram3        495.5M        [SWAP]                        
```
## USB
```
Bus 002 Device 002: ID 0bda:0411 Realtek Semiconductor Corp. 
Bus 002 Device 001: ID 1d6b:0003 Linux Foundation 3.0 root hub
Bus 001 Device 003: ID 13fe:4300 Kingston Technology Company Inc. 
Bus 001 Device 002: ID 0bda:5411 Realtek Semiconductor Corp. 
Bus 001 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub
```
## IP
```
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
       valid_lft forever preferred_lft forever
    inet6 ::1/128 scope host 
       valid_lft forever preferred_lft forever
2: dummy0: <BROADCAST,NOARP> mtu 1500 qdisc noop state DOWN group default qlen 1000
    link/ether 26:0c:6a:e5:6e:bb brd ff:ff:ff:ff:ff:ff
3: eth0: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc pfifo_fast state DOWN group default qlen 1000
    link/ether 00:04:4b:e6:88:dc brd ff:ff:ff:ff:ff:ff
4: l4tbr0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP group default qlen 1000
    link/ether 42:89:7a:6b:07:a9 brd ff:ff:ff:ff:ff:ff
    inet 192.168.55.1/24 brd 192.168.55.255 scope global l4tbr0
       valid_lft forever preferred_lft forever
    inet6 fe80::1/128 scope link 
       valid_lft forever preferred_lft forever
    inet6 fe80::4089:7aff:fe6b:7a9/64 scope link 
       valid_lft forever preferred_lft forever
5: rndis0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast master l4tbr0 state UP group default qlen 1000
    link/ether 42:89:7a:6b:07:a9 brd ff:ff:ff:ff:ff:ff
    inet6 fe80::4089:7aff:fe6b:7a9/64 scope link 
       valid_lft forever preferred_lft forever
6: usb0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast master l4tbr0 state UP group default qlen 1000
    link/ether 42:89:7a:6b:07:ab brd ff:ff:ff:ff:ff:ff
    inet6 fe80::4089:7aff:fe6b:7ab/64 scope link 
       valid_lft forever preferred_lft forever
8: br-03f13d45c756: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP group default 
    link/ether 02:42:26:40:95:9e brd ff:ff:ff:ff:ff:ff
    inet 172.18.0.1/16 brd 172.18.255.255 scope global br-03f13d45c756
       valid_lft forever preferred_lft forever
    inet6 fe80::42:26ff:fe40:959e/64 scope link 
       valid_lft forever preferred_lft forever
9: br-049e02835ba3: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP group default 
    link/ether 02:42:22:40:98:28 brd ff:ff:ff:ff:ff:ff
    inet 172.19.0.1/16 brd 172.19.255.255 scope global br-049e02835ba3
       valid_lft forever preferred_lft forever
    inet6 fe80::42:22ff:fe40:9828/64 scope link 
       valid_lft forever preferred_lft forever
10: docker0: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc noqueue state DOWN group default 
    link/ether 02:42:e4:62:bd:0f brd ff:ff:ff:ff:ff:ff
    inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0
       valid_lft forever preferred_lft forever
12: veth7583f17@if11: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue master br-049e02835ba3 state UP group default 
    link/ether a2:79:3f:fe:16:b0 brd ff:ff:ff:ff:ff:ff link-netnsid 0
    inet6 fe80::a079:3fff:fefe:16b0/64 scope link 
       valid_lft forever preferred_lft forever
14: veth8c341a5@if13: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue master br-03f13d45c756 state UP group default 
    link/ether 46:93:b3:c3:d9:b8 brd ff:ff:ff:ff:ff:ff link-netnsid 2
    inet6 fe80::4493:b3ff:fec3:d9b8/64 scope link 
       valid_lft forever preferred_lft forever
16: veth306ad93@if15: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue master br-049e02835ba3 state UP group default 
    link/ether d6:61:59:33:1f:e0 brd ff:ff:ff:ff:ff:ff link-netnsid 1
    inet6 fe80::d461:59ff:fe33:1fe0/64 scope link 
       valid_lft forever preferred_lft forever
18: veth975c0db@if17: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue master br-049e02835ba3 state UP group default 
    link/ether 56:70:6e:ab:aa:12 brd ff:ff:ff:ff:ff:ff link-netnsid 3
    inet6 fe80::5470:6eff:feab:aa12/64 scope link 
       valid_lft forever preferred_lft forever
default via 192.168.55.100 dev l4tbr0 metric 32766 
169.254.0.0/16 dev br-03f13d45c756 scope link metric 1000 
172.17.0.0/16 dev docker0 proto kernel scope link src 172.17.0.1 linkdown 
172.18.0.0/16 dev br-03f13d45c756 proto kernel scope link src 172.18.0.1 
172.19.0.0/16 dev br-049e02835ba3 proto kernel scope link src 172.19.0.1 
192.168.55.0/24 dev l4tbr0 proto kernel scope link src 192.168.55.1 
```
## dmesg errors
```
```
