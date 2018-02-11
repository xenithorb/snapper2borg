#!/usr/bin/env python3

BORG_BACKUP_PATH = "/mnt/external1/backups"
BORG_COMPRESSION = "auto,zstd"
BORG_NICENESS = "19"
BORG_IO_NICENESS = "7"
BORG_FLAGS = "-x -s"
# BORG_FLAGS = "-x -s -p"
BORG_PRUNE_FLAGS = "--keep-within 1d -d 10 -w 10 -m 6"
# BORG_PASSPHRASE = "${BORG_PASSPHRASE}"
BORG_PASSCOMMAND = "cat /root/.borg_password"
BORG_ENCRYPTION = "repokey-blake2"
BIND_MNT_PREFIX = "/tmp/borg"

# Note: "repo" is formerly "config", but I will likely use "config"
# here in python to implement an actual configuration. (to remove the above)


def check_root():
    """Return successful if we are the root user."""
    pass


def mutex():
    """Checks to make sure the script isn't running already."""
    pass


def get_last_snapshot(repo):
    """
    Outputs the name of the most recent snapshot.

    REMOVEME: Formerly get_latest()
    """
    pass


def snapper_mount_snapshot(repo, number, action):
    """
    Uses snapper's built-in mount command to mount a snapshot.

    `snapper -c <config> <mount/umount> <num>`
    REMOVEME: Formerly mount_snapshot(), Param "action" formerly "type"
    """
    pass


def borg():
    """Overload borg to include niceness... do we need this in py?"""


def borg_repo_create(repo):
    """
    Creates a borg repository.

    Presumably this would be used after checking for an already existing repo,
    then using this to create a blank one.

    REMOVEME: Formerly borg_create_repo()
    """
    pass


def borg_repo_prune(repo):
    """
    Runs `borg prune` with options.

    Should be called when SYSTEMD_INSTANCE == "snapper-cleanup"

    REMOVEME: Formerly borg_prune_repo()
    """
    pass


def borg_archive_create(repo, number, source):
    """
    Create a borg archive from a filesystem source.

    REMOVEME: Formerly borg_create_snap()
    """
    pass


def borg_archive_get_list(repo):
    """
    Gets a full list of the archives in a repo.

    REMOVEME: Formerly borg_get_names(), Param "source" formerly mount.
    """
    pass


def bind_mount_snapshot(repo, snapper_mount_path):
    """Bind mounts a snapshot to a common path under BIND_MNT_PREFIX."""
    pass


def wrap_up():
    """Do we need this? For exit handling"""
    pass
