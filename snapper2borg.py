#!/usr/bin/env python3
"""
A service to backup snapper's lvm snapshots to a borg repository.

Snapper2Borg is a script designed to be run as a systemd service that is kicked
off by snapper's timer through systemd.unit After= and Requires=. It has the
effect of being run after snapper in order to mount, then use the backup suite
`borg` in order to backup the LVM snapshot to a borg repository. The
inspiration for Snapper2Borg is/was btrbk and btrfs send/receive from the days
when I was using btrfs as a primary filesystem.
"""

import sys
import os
import configparser
# import pdb

config = configparser.ConfigParser()
config.read(['config.ini', 'config.cfg'])


class Instance:
    """Use the Mutex class to ensure running only one instance of Instance."""

    def __init__(self, args):
        """Instance class init."""
        self.args = args
        self.path = self.args[0]
        self.mutex = Mutex(self.path)

    def check_root(self):
        """Check if the script is running as root."""
        if os.geteuid() == 0:
            return True

    def wrap_up(self):
        """Do stuff before the program exits."""
        self.mutex.unlock()

    def run(self):
        """Run the main function or exit because we couldn't get a lock."""
        try:
            if not self.check_root():
                sys.stderr.write("You need to be root to use this script.\n")
                sys.exit(1)
            if self.mutex.lock():
                main(self)
            else:
                sys.stderr.write(
                    f"{os.path.basename(self.path)} is already running!\n")
                sys.exit(1)
        finally:
            self.wrap_up()


class Mutex:
    """Creates a new mutex on a file."""

    fcntl = __import__('fcntl')

    def __init__(self, path):
        """Mutex class init."""
        self.path = open(os.path.abspath(path))

    def lock(self):
        """Lock the file."""
        try:
            # sys.stderr.write("Locking: " + self.path.name + "\n")
            self.fcntl.flock(self.path.fileno(),
                             self.fcntl.LOCK_EX | self.fcntl.LOCK_NB)
            return True
        except OSError:
            sys.stderr.write("File is already locked!\n")
            return False

    def unlock(self):
        """Unlock the file."""
        try:
            # sys.stderr.write("Unlocking: " + self.path.name + "\n")
            self.fcntl.flock(self.path.fileno(), self.fcntl.LOCK_UN)
            return True
        except OSError:
            sys.stderr.write("Unknown error unlocking\n")
            return False


class Snapper:
    """
    Interact with `snapper` through its system dbus interface.

    See: https://github.com/openSUSE/snapper/tree/master/examples/python
    """

    def __init__(self):
        """Snapper class init."""
        import dbus
        self.bus = dbus.SystemBus()
        self.snapper = dbus.Interface(
            self.bus.get_object('org.opensuse.Snapper',
                                '/org/opensuse/Snapper'),
            dbus_interface='org.opensuse.Snapper')

    def get_last(self, repo):
        """
        Output the name of the most recent snapshot.

        REMOVEME: Formerly get_latest()
        """
        pass

    def mount(self, repo, number, action):
        """
        Use snapper's built-in mount command to mount a snapshot.

        `snapper -c <config> <mount/umount> <num>`
        REMOVEME: Formerly mount_snapshot(), Param "action" formerly "type"
        """
        pass

    def get_configs(self):
        """Return a list of snapper configs."""
        return self.snapper.ListConfigs()

    def list_snapshots(self, repo):
        """Return a list of all snapper snapshots."""
        import json
        # from time import gmtime, asctime
        # from pwd import getpwuid
        snapshots = self.snapper.ListSnapshots(repo)
        print(json.dumps(snapshots, indent=4))
        # for snapshot in snapshots:
        #     print(snapshot[0], snapshot[1], snapshot[2])
        #
        #     if snapshot[3] != -1:
        #         print(asctime(gmtime(snapshot[3])))
        #     else:
        #         print("now")
        #
        #     print(getpwuid(snapshot[4])[0], snapshot[5], snapshot[6])
        #     for k, v in snapshot[7].items():
        #         print("%s=%s" % (k, v))


class Borg:
    """Interact with borgbackup through its json output."""

    shutil = __import__('shutil')
    sub = __import__('subprocess')
    json = __import__('json')

    borg_path = shutil.which('borg')
    to_export = {
        "BORG_KEY_FILE": config['BORG_ENV']['KEY_FILE'],
        "BORG_PASSPHRASE": config['BORG_ENV']['PASSPHRASE'],
        "BORG_PASSCOMMAND": config['BORG_ENV']['PASSCOMMAND']
    }
    # Export the vaules that exist
    for k, v in to_export.items():
        if bool(v):
            os.environ[k] = v

    def __init__(self, repo):
        """Borg class init."""
        self.repo = repo
        self.repo_path = f"{config['BORG_REPO']['BACKUP_PATH']}/{self.repo}"

    def borg(self, args):
        """Call the borg command with an arguments list and return json."""
        cmd = [self.borg_path, '--log-json'] + args
        borg_run = self.sub.run(
            cmd, stderr=self.sub.PIPE, stdout=self.sub.PIPE)
        stdout = borg_run.stdout
        stderr = borg_run.stderr
        if bool(stderr):
            for val in stderr.decode().split('\n'):
                try:
                    sys.stderr.write(
                        self.json.dumps(self.json.loads(val), indent=4))
                except self.json.JSONDecodeError:
                    sys.stderr.write(f"{val}\n")
        return stdout

    def init(self):
        """
        Create a borg repository.

        Presumably this would be used after checking for an already existing
        repo, then using this to create a blank one.
        """
        encryption = f"-e {config['BORG_REPO']['ENCRYPTION']}"
        args = ["init", encryption, self.repo_path]
        return self.borg(args)

    def prune(self):
        """
        Run `borg prune` with options.

        Should be called when SYSTEMD_INSTANCE == "snapper-cleanup"
        """
        search = f"-a {config['BORG_ARCHIVE']['ARCHIVE_SEARCH']}"
        prune_flags = config['BORG_OPTIONS']['PRUNE_FLAGS']
        args = ["prune", search, prune_flags, self.repo_path]
        return self.borg(args)

    def create(self, number, source):
        """Create a borg archive from a filesystem source."""
        args = ["create"]
        compression = config['BORG_REPO']['COMPRESSION']
        if bool(compression):
            args.append(f"-C {compression}")
        archive = f"{self.repo_path}::{{hostname}}-{self.repo}" \
            + f"{config['BORG_ARCHIVE']['ARCHIVE_SUFFIX']}{number}-{{now}}"
        args.extend([archive, source])
        return self.borg(args)

    def list(self):
        """Get a full list of the archives in a repo."""
        args = ["list", "--json", self.repo_path]
        return self.borg(args)


def bind_mount_snapshot(repo, snapper_mount_path):
    """Bind mounts a snapshot to a common path under BIND_MNT_PREFIX."""
    pass


def main(self):
    """."""
    import json
    # snap = Snapper()
    # snap.list_snapshots('root')
    # borg = Borg('/mnt/external1/backups/root')
    # print(json.dumps(borg.list()['repository'], indent=4))
    borg = Borg('root')

    try:
        print(json.dumps(json.loads(borg.list()), indent=4))
    except json.JSONDecodeError:
        pass


if __name__ == "__main__":
    """
    Anything outside of an instance class is not guaranteeed to
    have a mutex.
    """
    app = Instance(sys.argv)
    app.run()
