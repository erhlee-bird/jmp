Jmp
===

Introduction
------------

Jmp is a python3 utility meant to be used to empower your file system navigation
experience. It's a directory bookmarking system which I will explain below.

Example
-------

With jmp I can set up really simple bookmarks.

``` {.example}
cd /home/user/project/development/piece1/src=

jmp work .  # Store absolute path to this directory as a bookmark called work.
```

Then in the future I can just run

``` {.example}
jmp work
```

The bookmarks are stored as absolute paths by default, but relative paths can
be stored as well.

``` {.example}
jmp -r up2 ../..

cd /home/user/project/development
jmp up2     # Path will now point to /home/user
```

Storage
-------

Bookmarks are stored as pickle files in "${HOME}/.jmp_pad/jmp_table.pkl".
