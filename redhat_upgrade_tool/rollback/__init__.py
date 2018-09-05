
import os

rhel6_profile = "98c3edb"
snapshot_metadata_file = "/boot/grub/snapshot.metadata"
rollback_dir = "/boot/rollback"
active_kernel_file = os.path.join(rollback_dir, '.active-kernel')
all_kernels_file = os.path.join(rollback_dir, '.all-kernels')
target_kernel_file = os.path.join(rollback_dir, '.target-kernel')
snap_boot_files_file = os.path.join(rollback_dir, '.snap_boot_files')
