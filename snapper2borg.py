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

import sys, os
from time import sleep

class Instance:
    """Use mutexes to ensure running only one instance of Instance"""

    def __init__(self, args):
        self.args = args
        self.path = self.args[0]
        self.mutex = Mutex(self.path)

    def check_root(self):
        if os.geteuid() == 0:
            return True

    def wrap_up(self):
        """Do stuff before the program exits"""
        self.mutex.unlock()

    def run(self):
        """Run the main function or exit because we couldn't get a lock"""
        try:
            if not self.check_root():
                sys.stderr.write("You need to be root to use this script.\n")
                sys.exit(1)
            if self.mutex.lock():
                main(self)
            else:
                sys.stderr.write(
                    os.path.basename(self.path) + " is already running!\n"
                )
                sys.exit(1)
        finally:
            self.wrap_up()

class Mutex:
    """Creates a new mutex on a file"""
    fcntl = __import__('fcntl')
    def __init__(self, path):
        self.path = open(os.path.abspath(path))

    def lock(self):
        """Lock the file"""
        try:
            sys.stderr.write("Locking: " + self.path.name + "\n")
            self.fcntl.flock(
                self.path.fileno(),
                self.fcntl.LOCK_EX | self.fcntl.LOCK_NB
            )
            return True
        except OSError:
            sys.stderr.write("File is already locked!\n")
            return False

    def unlock(self):
        """Unlock the file"""
        try:
            sys.stderr.write("Unlocking: " + self.path.name + "\n")
            self.fcntl.flock(self.path.fileno(), self.fcntl.LOCK_UN)
            return True
        except OSError:
            sys.stderr.write("Unknown error unlocking\n")
            return False

class Snapper:
    """https://github.com/openSUSE/snapper/tree/master/examples/python"""
    def __init__(self):
        import dbus
        self.bus = dbus.SystemBus()
        self.snapper = dbus.Interface(
            self.bus.get_object(
                            'org.opensuse.Snapper',
                            '/org/opensuse/Snapper'
                        ),
            dbus_interface='org.opensuse.Snapper'
        )

    def get_last(self, repo):
        """
        Outputs the name of the most recent snapshot.

        REMOVEME: Formerly get_latest()
        """
        pass


    def mount(self, repo, number, action):
        """
        Uses snapper's built-in mount command to mount a snapshot.

        `snapper -c <config> <mount/umount> <num>`
        REMOVEME: Formerly mount_snapshot(), Param "action" formerly "type"
        """
        pass

    def get_configs(self):
        """Print a list of snapper configs"""
        return self.snapper.ListConfigs()

    def list_snapshots(self, repo):
        from time import gmtime, asctime
        from pwd import getpwuid
        snapshots = self.snapper.ListSnapshots(repo)
        for snapshot in snapshots:
            print(snapshot[0], snapshot[1], snapshot[2])

            if snapshot[3] != -1:
                print(asctime(gmtime(snapshot[3])))
            else:
                print("now")

            print(getpwuid(snapshot[4])[0], snapshot[5], snapshot[6])
            for k, v in snapshot[7].items():
                print("%s=%s" % (k, v))


class Borg:
    """`borg` handler"""
    shutil = __import__('shutil')
    sub = __import__('subprocess')
    json = __import__('json')
    borg_path = shutil.which('borg')

    def __init__(self, repo):
        self.repo = repo

    def init(self):
        """
        Creates a borg repository.

        Presumably this would be used after checking for an already existing repo,
        then using this to create a blank one.

        REMOVEME: Formerly borg_create_repo()
        """
        pass


    def prune(self):
        """
        Runs `borg prune` with options.

        Should be called when SYSTEMD_INSTANCE == "snapper-cleanup"

        REMOVEME: Formerly borg_prune_repo()
        """
        pass


    def create(repo, number, source):
        """
        Create a borg archive from a filesystem source.

        REMOVEME: Formerly borg_create_snap()
        """
        pass


    def list(self):
        """
        Gets a full list of the archives in a repo.

        REMOVEME: Formerly borg_get_names(), Param "source" formerly mount.
        """
        args = [self.borg_path, "list", "--json", self.repo]
        list_json = self.json.loads(self.sub.run(args, stdout=self.sub.PIPE).stdout)
        print(self.json.dumps(list_json, indent=4))



def bind_mount_snapshot(repo, snapper_mount_path):
    """Bind mounts a snapshot to a common path under BIND_MNT_PREFIX."""
    pass


def main(self):
    snap = Snapper()
    snap.list_snapshots('root')
    borg = Borg('/mnt/external1/backups/root')
    borg.list()
    pass

if __name__ == "__main__":
        app = Instance(sys.argv)
        app.run()
