import os
import shutil
import types

import jmp

store = "/tmp/jmp_pad_unittest"
shutil.rmtree(store)
backend = jmp.JmpBackend(path=store)
backend.SUPPRESS = True


def log(msg, depth=1):
    print('\t' * depth + msg)


def _test_():
    log("Unit test suite. Test functions start with '_test_'")
    log("Unit tests return 0 for success, 1 for failure, and -1 if not a test.")
    return -1


def _test_store_basic():
    """
    Test to make sure that jmp can store and load from the table.
    """
    with backend:
        return 0 if backend.store_jmp("test_store_basic", "/tmp") else 1

def _test_store_relative():
    """
    Test to make sure that jmp can store relative paths.
    """
    os.chdir(store)
    with backend:
        backend.store_jmp("test_store_relative", "..", absolute=False)
        return 0 if backend.jmp_table["test_store_relative"].target == ".." \
               else 1

def _test_basic_store_tag_expand():
    """
    Test to make sure that jmp can store tag relative paths.
    """
    with backend:
        backend.store_jmp("test_store_tag_expand",
                          "test_store_basic/jmp_pad_unittest")
        return 0 if backend.jmp_to("test_store_tag_expand") else 1

def _test_tag_suite():
    """
    Test the various different path conditions for a tag.
    """
    os.chdir(os.path.expanduser("~"))
    with backend:
        backend.store_jmp("test_home_abs", "/home/")
        backend.store_jmp("test_home_rel", "..")
        backend.store_jmp("test_home_usr", "~/..")
        backend.store_jmp("test_home_env", "$HOME/..")
        backend.store_jmp("test_home_tag", "test_home_abs")

        sum = 0
        sum |= 0 if backend.jmp_to("test_home_abs") else 1
        sum |= 0 if backend.jmp_to("test_home_rel") else 1
        sum |= 0 if backend.jmp_to("test_home_usr") else 1
        sum |= 0 if backend.jmp_to("test_home_env") else 1
        sum |= 0 if backend.jmp_to("test_home_tag") else 1
        return sum

if __name__ == "__main__":
    local_functions = [val for val in dict(locals()).values()
                       if isinstance(val, types.FunctionType)]
    tests = [test for test in local_functions
             if test.func_name.startswith('_test_')]
    fails = 0
    total = len(tests)
    for f in tests:
        log("Testing: {}".format(f.func_name), depth=0)
        ret = f()
        if ret < 0:
            total -= 1
        else:
            log("Test {} {}".format(f.func_name, ("Passed", "Failed")[ret]))
            fails += ret
        print("")
    print("Tests Passed: {} / {}".format(total - fails, total))
