#!/usr/bin/env python
#
# run-tests.py - Run a set of tests on Mercurial
#
# Created 2011 by A. McClure, you may consider this file public domain
#

import sys
import os
import subprocess

args = sys.argv[1:]
do_build = 'build' in args or 'run' in args

versions = ['1.9.2', '1.9', '1.8.4', '1.8']

# I'm not doing any path correctness right now, this will probably break hard on Windows
scratch_path = "ves_scratch/"
mercurial_path = scratch_path + "hg"
baserev_path = "envs/"

# At what path would an env with this hg tag be stored?
def rev_path(rev):
    return baserev_path + str(rev)

# Get a scratch copy of the mercurial repository.
def ensure_mercurial():
    if not os.path.isdir(mercurial_path):
        print("\t-- Downloading mercurial")
        subprocess.call(["mkdir", "-p", scratch_path])
        subprocess.call(["hg", "clone", "http://selenic.com/hg", mercurial_path])
    pass
    
# Set up an environment for the given version of hg.
def ensure_env(version):
    path = rev_path(version)
    if not os.path.isdir(path):
        print("\t-- Setting up version %s" % version)
        ensure_mercurial()
        subprocess.call(["mkdir", "-p", baserev_path])
        # TODO

# Act
if do_build:
    for version in versions:
        ensure_env(version)
else:
    print("Usage:")
    print("\t./virtualenv-setup.py build")