#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from subprocess import Popen, PIPE
import sys

REPO_PATH = "/home/ed/projects/dabo"
SERVER_PATH = "/home/ed/projects/webupdate"
VERSION_FILE = os.path.join(SERVER_PATH, "current_version")
NOTIFICATION_FILE = os.path.join(SERVER_PATH, "version_notice")


def runproc(cmd):
    proc = Popen([cmd], shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)
    return proc.communicate()


def main():
    cmd = """cd %s; git pull --all; git checkout master; git tag""" % REPO_PATH
    with file("/tmp/webupdate.log", "a") as logg:
        logg.write("Running: %s\n" % cmd)
    out, err = runproc(cmd)
    lines = [line.strip().replace("v", "") for line in out.splitlines()
            if line.startswith("v")]
    parts = [vers.split(".") for vers in lines]
    parts.sort(key=lambda part: (int(part[2]), int(part[1]), int(part[0])))
    vers = "v%s.%s.%s" % tuple(parts[-1])
    with file(VERSION_FILE, "w") as vfile:
        vfile.write(vers)


if __name__ == "__main__":
    vers_time = os.stat(VERSION_FILE).st_mtime
    notification_time = os.stat(NOTIFICATION_FILE).st_mtime
    if vers_time > notification_time:
        print "VERS:", vers_time, "NOTIF:", notification_time
        sys.exit()
    main()
