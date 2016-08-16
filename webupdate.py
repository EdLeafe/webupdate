import datetime
import logging
import json
import os
from subprocess import Popen, PIPE
import tempfile
from zipfile import ZipFile

from flask import Flask
from flask import request
app = Flask(__name__)


logger = app.logger
handler = logging.FileHandler("/home/ed/projects/webupdate/logs/webupdate.log")
logger.addHandler(handler)
logger.setLevel(logging.INFO)

#PREFIX = "dabo-"
PREFIX = "v"
REPO_PATH = "/home/ed/projects/dabo"
SERVER_PATH = "/home/ed/projects/webupdate"
NOTIFICATION_FILE = os.path.join(SERVER_PATH, "version_notice")
VERSION_FILE = os.path.join(SERVER_PATH, "current_version")


def logit(msg, method=logger.info):
    tm = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    method("%s - %s" % (tm, msg))


def runproc(cmd):
    logit("runproc called with: %s" % cmd)
    proc = Popen([cmd], shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)
    return proc.communicate()


def set_notification():
    cmd = "touch %s/version_notice" % SERVER_PATH
    out, err = runproc(cmd)


def get_current_version():
    with file(VERSION_FILE, "r") as vfile:
        return vfile.read()


class VersionChange(object):
    def __init__(self, version):
        self.version = version
        self.curr_version = get_current_version()

    def get_release_notes(self):
        cmd = """cd %s; git log --pretty=format:"%%cr:%%s" %s..%s """ % (
                REPO_PATH, self.version, self.curr_version)
        out, err = runproc(cmd)
        self.notes = [line.split(":", 1) for line in out.splitlines()]


    def get_changed_files(self):
        cmd = "cd %s; git diff --name-status %s..%s" % (REPO_PATH,
                self.version, self.curr_version)
        out, err = runproc(cmd)
        self.files = out.splitlines()


    def get_changes(self):
        self.get_release_notes()
        self.get_changed_files()
        return {'files': self.files, 'notes': self.notes}


    def get_files(self):
        currdir = os.getcwd()
        self.get_changed_files()
        delfiles = []
        goodPrefixes = ("dabo", "demo", "ide")
        os.chdir(REPO_PATH)
        fd, tmpname = tempfile.mkstemp(suffix=".zip")
        os.close(fd)
        z = ZipFile(tmpname, "w")
        zcount = dcount = 0
        for chg in self.files:
            chgtype, pth = chg.split()
            try:
                prfx, fname = pth.split("/", 1)
            except ValueError:
                # A file in the trunk; ignore
                continue
            if prfx not in goodPrefixes:
                # Not a web update project
                continue
            if "D" in chgtype:
                delfiles.append(pth)
                dcount += 1
                continue
            # 'pth' must be str, not unicode
            if os.path.isfile(pth):
                z.write(str(pth))
                zcount += 1
        if dcount:
            # Add the file with deletion paths
            fd, tmpdel = tempfile.mkstemp()
            os.close(fd)
            file(tmpdel, "w").write("\n".join(delfiles))
            z.write(tmpdel, self._deletedFilesName)
            os.remove(tmpdel)

        z.close()
        headers = {"content-type": "application/x-zip-compressed"}
        ret = file(tmpname).read()
        os.remove(tmpname)
        os.chdir(currdir)
        return (ret, None, headers)


@app.route("/currentversion")
def current_version():
    logit("Checking current version")
    return get_current_version()


@app.route("/webupdate/check/<version>")
def check_webupdate(version):
    logit("check_webupdate called with version = %s" % version)
    try:
        full_version = "%s%s" % (PREFIX, version)
        changes = VersionChange(full_version)
        resp = changes.get_changes()
        return json.dumps(resp)
    except Exception as e:
        logit("check_webupdate error: %s" % e, logger.error)
        return str(e)


@app.route("/webupdate/files/<version>")
def webupdate_files(version):
    logit("webupdate_files called for version %s" % version)
    full_version = "%s%s" % (PREFIX, version)
    changes = VersionChange(full_version)
    resp = changes.get_files()
    logit("webupdate_files returning: %s bytes" % len(resp[0]))
    return resp


@app.route("/github/", methods=["POST"])
def github_hook():
    """
    There has been an update on GitHub. It could be to either the
    master or working branch, but just to be safe, update the current
    tag for master.
    """
    logit("GitHub hook called")
    set_notification()
    return ""

@app.route("/eventlet/<seq>")
def test_delay(seq=None):
    import random
    import time
    tm = random.randrange(0, 3)
    logit("%s START" % seq)
    time.sleep(tm)
    logit("%s STOP" % seq)

    return "%s" % tm


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
