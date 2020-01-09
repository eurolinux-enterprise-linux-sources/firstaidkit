# First Aid Kit - diagnostic and repair tool for Linux
# Copyright (C) 2008 Joel Andres Granados <jgranado@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from pyfirstaidkit.plugins import Plugin,Flow
from pyfirstaidkit.returns import *
from pyfirstaidkit.utils import *
from pyfirstaidkit.reporting import PLUGIN
from pyfirstaidkit.issue import SimpleIssue
from pyfirstaidkit import Config
from pyfirstaidkit.errors import *

import os.path

class MdadmConfig(Plugin):
    """ Addresses the validity and presence of /etc/mdadm.conf """
    flows = Flow.init(Plugin)
    name = "mdadm configuration"
    version = "0.0.1"
    author = "Joel Andres Granados"
    description = "Assess the validity and existence of the mdadm.conf file"

    @classmethod
    def getDeps(cls):
        return set(["root", "filesystem"])

    def __init__(self, *args, **kwargs):
        Plugin.__init__(self, *args, **kwargs)
        self.currentFileDict = {} #what we read from /etc/mdadm.conf
        self.scannedFileDict = {} #what `mdadm --misc --detail --scan`
        self.scannedFile = None # what `mdadm --misc --detail --scan` returns
        self.configFile = os.path.join(Config.system.root,"/etc/mdadm.conf")
        self.backupSpace = self._backups.getBackup(str(self))
        self._issue = SimpleIssue(self.name, "mdadm.con misconfigured")

    def prepare(self):
        # We read the configuration file if it exists
        if os.path.exists(self.configFile):
            self._reporting.info("Gathering information from %s."%
                    self.configFile, level = PLUGIN, origin = self)
            fd = open(self.configFile, "r")
            for line in fd.readlines():
                splitline = line.strip("\n").split(" ")
                if "ARRAY" in splitline:
                    self.currentFileDict[splitline[1]] = splitline
            fd.close()

        else:
            self._reporting.info("File %s was not found."%
                    self.configFile, level = PLUGIN, origin = self)

        # We execute the mdadm command
        self._reporting.info("Scanning for software raid with mdadm.",
                level = PLUGIN, origin = self)
        mdadmargs = ["--misc", "--detail", "--scan"]
        proc = spawnvch(executable = "mdadm", args = mdadmargs,
                chroot = Config.system.root)
        (out, err) = proc.communicate()

        if err == '':
            # means that the command ran with no errors.
            for line in out.__str__().split("\n"):
                splitline = line.strip("\n").split(" ")
                if "ARRAY" in splitline:
                    self.scannedFileDict[splitline[1]] = splitline
            self.scannedFile = out
        else:
            # This should make the flow go to clean.  If there is an error we
            # should not trust what mdadm tells us.
            self._reporting.info("The mdadm command had the following " \
                    "error:%s. The plugin will silently exit."%err,
                    level = PLUGIN, origin = self)
            self._result = None
            return
        self._result = ReturnSuccess
        self._issue.set(reporting = self._reporting, level = PLUGIN,
                origin = self)

    def diagnose(self):
        # If nothing was returned by the mdadm command.  we dont have software
        # raid.
        if len(self.scannedFileDict) == 0:
            self._reporting.info("There was no sofware raid found by the " \
                    "mdadm command.... Nothing to do.", level = PLUGIN,
                    origin = self)
            self._result = ReturnSuccess
            self._issue.set(checked=True, happened=False,
                    reporting=self._reporting, level=PLUGIN, origin=self)
            return

        # If nothing is detected the result is successfull.
        self._result = ReturnSuccess

        # If there is one difference between the configs, regarding the
        # ARRAYS.  We replace the config file. Lets check for missing arrays
        # in the curren config file.
        for key, value in self.scannedFileDict.iteritems():
            if not self.currentFileDict.has_key(key):
                self._reporting.info("Found that the current mdadm.conf is " \
                        "missing: %s."%value, level = PLUGIN, origin = self)
                self._result = ReturnFailure

        # Lets check for additional ARRAYS that should not be there.
        for key, value in self.currentFileDict.iteritems():
            if not self.scannedFileDict.has_key(key):
                self._reporting.info("The followint entry: %s, is in the " \
                        "config file but was not detected by mdadm."%value,
                        level = PLUGIN, origin = self)
                self._result = ReturnFailure

        if self._result == ReturnSuccess:
            self._reporting.info("There was no problem found with the " \
                    "current mdadm.conf file.", level = PLUGIN, origin = self)

        self._issue.set(checked = True,
                happened = (self._result == ReturnFailure),
                reporting = self._reporting, level = PLUGIN, origin = self)

    def backup(self):
        if os.path.isfile(self.configFile):
            self._reporting.info("Making a backup of %s."%
                    self.configFile, level = PLUGIN, origin = self)
            self.backupSpace.backupPath(self.configFile)

        else:
            self._reporting.info("It appears that the file %s does not "\
                    "exist.  No backup attempt will be made."%self.configFile,
                    level = PLUGIN, origin = self)

        self._result = ReturnSuccess

    def fix(self):
        try:
            self._reporting.info("Going to write configuration to %s."%
                    self.configFile, level = PLUGIN, origin = self)
            fd = open(self.configFile, "w")
            fd.write("# File created by Firstaidkit.\n")
            fd.write("# DEVICE partitions\n")
            fd.write("# MAILADDR root\n")
            fd.write(self.scannedFile)
            fd.close()
            self._reporting.info("Configuration file writen.", level = PLUGIN,
                    origin = self)

            # The original mdadm.conf will be restore to
            # mdadm.conf.firstaidkit, just in case.
            self._reporting.info("Will put the old mdadm.conf in %s."%
                    os.path.join(Config.system.root,
                        self.configFile+".firstaidkit"), level=PLUGIN,
                    origin=self)
            self.backupSpace.restoreName(self.configFile,
                    path = self.configFile+".firstaidkit")
            self._result = ReturnSuccess

        except IOError:
            fd.close()
            self._reporting.info("Error occurred while writing %s."%
                    self.configFile, level = PLUGIN, origin = self)
            self._result = ReturnFailure
        self._issue.set(fixed = (self._result == ReturnSuccess),
                reporting = self._reporting, level = PLUGIN, origin = self)

    def restore(self):
        if not self.backupSpace.exists(self.configFile):
            # This is the case where there is no config file.
            self._reporting.info("The backedup file was not present. " \
                    "Assuming that %s was ont present to begin with."%
                    self.configFile, level = PLUGIN, original = self)
        else:
            self._reporting.info("Restoring original file.", level = PLUGIN ,
                    origin = self)
            self.backupSpace.restoreName(self.configFile)
        self._result = ReturnSuccess

    def clean(self):
        self._result = ReturnSuccess

def get_plugin():
    return MdadmConfig

