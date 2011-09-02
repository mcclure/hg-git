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

dulwich_version = "dulwich-0.8.0"

# I'm not doing any path correctness right now, this will probably break hard on Windows
scratch_path = "ves_scratch/"
mercurial_path = scratch_path + "hg"
dulwich_path = scratch_path + "dulwich"
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
        
# Get a copy of the dulwich repository and move it to the single desired version.
# Notice it would be easy to test for a range of dulwiches as is currently done with mercurial.
def ensure_dulwich():
    if not os.path.isdir(dulwich_path):
        print("\t--Downloading dulwich")
        subprocess.call(["mkdir", "-p", scratch_path])
        subprocess.call(["hg", "clone", "git://git.samba.org/jelmer/dulwich.git", dulwich_path])
        subprocess.call(["hg", "-R", dulwich_path, "up", dulwich_version])
    
# Set up an environment for the given version of hg.
def ensure_env(version):
    path = rev_path(version)
    if not os.path.isdir(path):
        print("\t-- Setting up version %s" % version)
        ensure_mercurial()
        ensure_dulwich()
        subprocess.call(["mkdir", "-p", baserev_path])
        print("\t-- Making virtualenv" % version)
        subprocess.call(["virtualenv", path])
        print("\t-- Loading appropriate mercurial" % version)
        subprocess.call(["hg", "-R", mercurial_path, "up", version])
        # TODO: Install mercurial and Dulwich to new env.

# Act
if do_build:
    for version in versions:
        ensure_env(version)
else:
    print("Usage:")
    print("\t./virtualenv-setup.py build")