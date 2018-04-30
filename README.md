Jmp
===

Introduction
------------

Jmp is a bash/python3 utility meant to be used to empower your file system
navigation experience. It's a directory bookmarking system which I will explain
below.

Installation
------------

Jmp is designed as a function sourced by the shell that invokes the python3
'backend'.

The simplest installation is just adding a line to your bashrc as follows.

```
source /path/to/jmp/jmp
```

The installation script installs the bash completion entry to the prefix
provided by the -p option and adds the above line sourcing the jmp utility to
the target bashrc.

```
./scripts/install.sh -p /usr/ -b ${HOME}/.bashrc
```

Usage
-----

With jmp I can set up really simple bookmarks.

```
cd /home/user/project/development/piece1/src

jmp work .  # Store absolute path to this directory as a bookmark called work.
```

Then in the future I can just run

```
jmp work
```

The bookmarks are stored as absolute paths by default, but relative paths can
be stored as well.

```
jmp -r up2 ../..

cd /home/user/project/development
jmp up2     # Path will now point to /home/user
```

Storage
-------

Bookmarks are stored as pickle files in ="${HOME}/.jmp_pad/jmp_table.pkl"=.
