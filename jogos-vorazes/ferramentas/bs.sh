#!/bin/bash
D=/home/user/bambulab/bin/squashfs-root
export LC_ALL=C LD_LIBRARY_PATH=/home/user/bambulab/compat:$D/bin
exec "$D/bin/bambu-studio" "$@"
