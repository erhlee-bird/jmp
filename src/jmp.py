#!/usr/bin/python
"""
@file jmp
@author Eric Lee

Rather than use the built-in bash pushd and popd for managing
the directory stack. Run our own version to handle jump tables
that are more easily managed than adding custom aliases and
such to the bashrc file.

Operates as a functional replacement for cd.
Needs to be run as a shell function to properly change directories.
"""
import argparse
from contextlib import redirect_stdout
import os
import pickle
import subprocess
import sys

# Use for upgrading outdated jmp entries.
CURRENT_VERSION = 5


class JmpException(Exception):
    """
    Exceptions for the Jmp utility.
    """
    pass


def handle_args():
    """
    Create an argparser instance to handle arguments and return them.
    """
    parser = argparse.ArgumentParser(
        prog="jmp",
        description="".join((
            "Jmp utility to create directory aliases on the fly.\n\n",
            "  How to list tags:\n",
            "    jmp\n",
            "    jmp -l\n",
            "    jmp --ls\n\n",
            "  How to save tags:\n",
            "    jmp tagname path\n",
            "    jmp    h    '$HOME'\t\t# Can store paths with env vars\n",
            "    jmp    docs h/Documents\t# Can store tag-relative paths\n",
            "    jmp -r up2  ../..\t\t# Store relative paths\n",
            "    jmp    root ../..\t\t# This stores as an absolute path\n\n",
            "  How to delete tags:\n",
            "    jmp -d tagname\n\n",
            "  How to jump to tags:\n",
            "    jmp tagname\n",
            "    jmp h\n",
            "    jmp ..\t\t\t# Use just like cd for existing paths\n",
            "    jmp h/Documents\t\t# Tag-relative jumping\n",
        )),
        formatter_class=argparse.RawTextHelpFormatter)

    lgroup = parser.add_mutually_exclusive_group()
    lgroup.add_argument(
        "-l", "-ls", "--ls",
        dest="list",
        action="store_true",
        help="List the available aliases.")
    lgroup.add_argument(
        "--complete",
        dest="optlist",
        nargs="*",
        help="Expand jmp options for completion.")
    lgroup.add_argument(
        "--clear",
        action="store_true",
        help="Delete all of the tags from the jmp_table.")

    absgroup = parser.add_mutually_exclusive_group()
    absgroup.add_argument(
        "-a", "--absolute",
        dest="absolute",
        action="store_true",
        default=True,
        help="Store an absolute path. (default)")
    absgroup.add_argument(
        "-r", "--relative",
        dest="absolute",
        action="store_false",
        help="Store a relative path.")

    actgroup = parser.add_mutually_exclusive_group()
    actgroup.add_argument(
        "-d", "--delete",
        action="store_true",
        help="Delete a jump tag.")
    actgroup.add_argument(
        "-e", "--expand",
        action="store_true",
        help="Expand a jump path and print for use with other utilities.")

    parser.add_argument(
        "tag",
        nargs="?",
        help="The tag we want to create or jump to.")
    parser.add_argument(
        "target",
        nargs="?",
        help="The location we want our tag to jump to.")
    return parser, parser.parse_args()


class JmpStore(object):
    """
    Keep our jump targets standardized.
    """
    def __init__(self, flags, target):
        self.version = CURRENT_VERSION
        self.flags = flags
        self.target = target
        self.used = 0

    def upgrade(self):
        while self.version < CURRENT_VERSION:
            self.version += 1


class JmpBackend(object):
    """
    Class that handles setting up the utility.
    """
    USER_FLAG = 1 << 0
    TAG_FLAG = 1 << 1
    ENV_FLAG = 1 << 2
    LOG_DEBUG = False
    # Use to suppress all output.
    SUPPRESS = False

    def __init__(self, path="~/.jmp_pad", store="jmp_table.pkl"):
        """
        @param path The path where config and data files are stored.
        @param store The jmp table file store.
        """
        # Set up our storage directory.
        epath = os.path.expanduser(os.path.expandvars(path))
        if not os.path.isdir(epath):
            try:
                os.makedirs(epath)
                self.debug("Created new storage directory {}.".format(epath))
            except OSError:
                self.log("Could not make storage directory {}.".format(epath))
                sys.exit(1)
        self.path = epath
        self.store = store
        self.jmp_table = {}

    def log(self, msg, debug=False, fd=sys.stdout):
        """
        @brief Print a message.

        @param msg The message to be outputted.
        @param debug If true, only print the message if debug messages
                     are allowed.
        """
        if self.SUPPRESS:
            return
        if not debug or self.LOG_DEBUG:
            print(msg, file=fd)

    def debug(self, msg):
        """
        @brief Print a debug message.
        """
        self.log(msg, debug=True, fd=sys.stderr)

    def __enter__(self):
        self.load_table()

    def __exit__(self, type, value, traceback):
        self.save_table()

    def load_table(self):
        """
        Loads the stored jump table into the utility.
        """
        store_file = os.path.join(self.path, self.store)
        if os.path.isfile(store_file):
            try:
                with open(store_file, "rb") as store_file_data:
                    self.jmp_table = pickle.load(store_file_data)
            except EOFError:
                self.jmp_table = {}
        self.debug("Successfully loaded jmp table.")

    def save_table(self):
        """
        Saves the jump table back into the file store.
        """
        store_file = os.path.join(self.path, self.store)
        with open(store_file, "wb") as store_file_data:
            pickle.dump(self.jmp_table, store_file_data)
        self.debug("Successfully saved jmp table.")

    def print_list(self):
        """
        @brief Prints out the existing jump aliases.
               Include the targets as well.
        """
        self.log("jmp_table:")
        if not self.jmp_table:
            self.log("  empty")
        for jmp, store in sorted(self.jmp_table.items(),
                                 key=lambda j: -j[1].used):
            self.log("  {} ({}) -> {}".format(jmp, store.used, store.target))

    def completion(self, opts):
        """
        @brief Print out existing jmp aliases. Formatted for bash_completion.

        @return '"alias_1" "alias_2" "alias_3" ...'
        """
        # BUG: This needs fixing. The completion cur and prev are not reliable.
        cur = opts[-1] if len(opts) > 1 else None
        if cur and os.path.sep in cur:
            # Get a listing of the directory post expansion and only return the
            # directories.
            base, _ = os.path.split(cur)
            ebase = self.expand(*self.get_flags(base))
            try:
                os.chdir(ebase)
                alist = sorted([os.path.join(base, f)
                                for f in os.listdir(ebase)
                                if os.path.isdir(f)])
                formatfix = ['"{}"'.format(name) for name in alist]
                self.log(" ".join(formatfix))
            except OSError:
                pass
        else:
            output = []
            for jmp in sorted(self.jmp_table.keys(),
                              key=lambda k: -self.jmp_table[k].used):
                output.append('"{}"'.format(jmp))
            if not output:
                output = ['"{}"'.format(f) for f in os.listdir(".")]
            self.log(" ".join(output))

    def expand(self, flags, target):
        """
        @brief Expand a target according to the provided flags.

        @param flags The expand flag rules.
        @param target The target we want to expand.

        @return The expanded path or None.
        """
        if not flags:
            return target
        while flags:
            if flags & self.USER_FLAG:
                target = os.path.expanduser(target)
                flags ^= self.USER_FLAG
            elif flags & self.TAG_FLAG:
                splitpath = target.split(os.path.sep)
                store = self.jmp_table[splitpath[0]]
                splitpath[0] = self.expand(store.flags, store.target)
                target = os.path.sep.join(splitpath)
                flags ^= self.TAG_FLAG
            elif flags & self.ENV_FLAG:
                target = os.path.expandvars(target)
                flags ^= self.ENV_FLAG
            else:
                raise JmpException("Unexpected flag bit set.")
        return target

    def get_flags(self, target):
        """
        @brief Given a target, get the flags we would need to expand it.

        @param The target we want to generate flags for.

        @return A tuple of the flags and the target.
        """
        flags = 0
        if target.split(os.path.sep)[0] in self.jmp_table:
            # We have a nested tag.
            flags |= self.TAG_FLAG
        elif target.startswith("~"):
            # We need to expand the home directory.
            flags |= self.USER_FLAG
        if target != os.path.expandvars(target):
            # We have environment variables to expand.
            flags |= self.ENV_FLAG
        return (flags, target)

    def store_jmp(self, tag, target, absolute=True):
        """
        @brief Given a tag, store it in our jump table to point to the target
               only if the target is a valid existing directory.

        @param tag The tag we want to create.
        @param target The location we want to associate with our tag.
        @param absolute Whether or not we should store the absolute path.

        @return True if the jmp was added and False otherwise.
        """
        flags, target = self.get_flags(target)
        if not flags and absolute:
            target = os.path.abspath(target)
        if not os.path.isdir(self.expand(flags, target)):
            self.log("{} is not a jumpable directory.".format(target))
            return False
        self.jmp_table[tag] = JmpStore(flags, target)
        self.log("Added jmp {} -> {}".format(tag, target))
        return True

    def delete_jmp(self, tag):
        """
        @brief Delete a tag from our jump table.

        @param tag The tag we want to delete.

        @return True on success and False otherwise.
        """
        try:
            self.jmp_table.pop(tag)
            self.log("Deleted tag {}.".format(tag))
            return True
        except KeyError:
            self.log("Tag {} is not registered.".format(tag))
            return False

    def jmp_to(self, tag):
        """
        @brief Expand our tag and if it is a valid location, print it for
               the jmp bash function to consume.

        @param tag The tag we want to jump to. Can be a tag or a location.

        @return True on success, False otherwise.
        """
        special = ('-',)
        flags, target = self.get_flags(tag)
        path = self.expand(flags, target)
        if not os.path.isdir(path) and target not in special:
            self.log("Tag {} points to an invalid path.".format(tag), fd=sys.stderr)
            if flags & self.TAG_FLAG and tag in self.jmp_table:
                with redirect_stdout(sys.stderr):
                    if input("delete tag? (y/n): ").lower() == "y":
                        self.delete_jmp(tag)
                return False
            return False
        if flags & self.TAG_FLAG and tag in self.jmp_table:
            self.jmp_table[tag].used += 1
        self.log("bash: {}".format(path))
        return True

    def git_fzf(self):
        ret = subprocess.run(
            "git rev-parse --show-toplevel",
            check=False,
            shell=True,
            stderr=subprocess.DEVNULL,
            stdout=subprocess.PIPE
        )
        root_dir = os.getcwd()
        if ret.returncode == 0:
            root_dir = ret.stdout.decode().strip()

        # Get the relative path to the root_dir.
        ret = subprocess.run(
            f"realpath --relative-to=. {root_dir}",
            check=False,
            shell=True,
            stderr=subprocess.DEVNULL,
            stdout=subprocess.PIPE
        )
        relative_path = ""
        if ret.returncode == 0:
            relative_path = ret.stdout.decode().strip()

        ret = subprocess.run(
            "fzf --exact",
            check=False,
            cwd=root_dir,
            shell=True,
            # NB: Need stderr to show selection menu.
            # stderr=subprocess.DEVNULL,
            stdout=subprocess.PIPE
        )
        if ret.returncode == 0:
            path = ret.stdout.decode().strip()
            self.log("bash: {}".format("/".join([x for x in [relative_path, path] if x])))

    def default_action(self):
        self.git_fzf()


def main():
    """
    Run main.
    """
    _, args = handle_args()
    jmpback = JmpBackend()
    with jmpback:
        # If we have an optlist request, it takes precedence and we
        # print out the available jump targets for a completion script.
        if args.optlist:
            jmpback.completion(args.optlist)
        # If we have a list request, it takes next precedence.
        elif args.list:
            jmpback.print_list()
        # If we have a clear request, clear the jmp_table.
        elif args.clear:
            jmpback.jmp_table.clear()
        # If we have a tag and no target, either jump or delete it.
        elif args.tag and not args.target:
            if args.delete:
                jmpback.delete_jmp(args.tag)
            elif args.expand:
                jmpback.log(jmpback.expand(*jmpback.get_flags(args.tag)))
            else:
                jmpback.jmp_to(args.tag)
        # If we have a tag and a target, we can store the jump.
        elif args.tag and args.target:
            jmpback.store_jmp(args.tag, args.target, args.absolute)
        else:
            jmpback.default_action()

if __name__ == "__main__":
    main()
