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

import tempfile, subprocess, time, signal, os, os.path, shutil

class Xserver(Plugin):
    """ Plugin to detect an rescue faulty xserver configurations. """
    flows = Flow.init(Plugin)
    flows["force"] = Flow({
            Plugin.initial: {Return: "prepare"},
            "prepare"     : {ReturnSuccess: "diagnose2"},
            "diagnose2"   : {ReturnSuccess: "clean", ReturnFailure: "backup"},
            "backup"      : {ReturnSuccess: "fix", ReturnFailure: "clean"},
            "restore"     : {ReturnSuccess: "clean", ReturnFailure: "clean"},
            "fix"         : {ReturnSuccess: "clean", ReturnFailure: "restore"},
            "clean"       : {ReturnSuccess: Plugin.final}
          }, description="This flow skips the search for the xserver lock file")
    name = "X server"
    version = "0.0.1"
    author = "Joel Andres Granados"
    description = "Automates recovery of the xserver"

    @classmethod
    def getDeps(cls):
        return set(["root", "filesystem"])

    def __init__(self, *args, **kwargs):
        Plugin.__init__(self, *args, **kwargs)
        # Arbitrary test display
        self.display = ":10"
        self.confPath = "/etc/X11/xorg.conf"
        self.backupSpace = self._backups.getBackup(str(self))
        self._issue = SimpleIssue(self.name, "X server didn't start")

    def prepare(self):
        # Nothing to prepare really.
        self._result = ReturnSuccess
        self._issue.set(reporting = self._reporting, level = PLUGIN,
                origin = self)

    def diagnose(self):
        # Lets see if there is a server active.
        if os.path.exists("/tmp/.X0-lock"):
            self._reporting.info("An X server is already running.",
                    level = PLUGIN, origin = self)
            self._reporting.info("You can run the \"force\" flow to "
                    "avoud this check. In some cases it works.",
                    level = PLUGIN, origin = self)
            self._result = ReturnSuccess

        elif self.serverStart():
            self._reporting.info("Everything seems ok with the X server.",
                    level = PLUGIN, origin = self)
            self._result = ReturnSuccess

        elif not os.path.exists(self.confPath):
            # If the configuration is not there dont even bother to try
            #fixing it.  This will go through the proces of trying to fix
            #it.  at least we told the user.
            self._reporting.info("The error is in the xservers autodetection "
                    "mechanism, this does not have an automated solution yet.",
                    level = PLUGIN, origin = self)
            self._result = ReturnFailure

        else:
            self._reporting.info("X server is missconfigured.", level = PLUGIN,
                    origin = self)
            self._result = ReturnFailure
        self._issue.set(checked = True,
                happened = (self._result == ReturnFailure),
                reporting = self._reporting, level = PLUGIN, origin = self)

    def diagnose2(self):
        """Just a diagnose without the lock check"""
        if self.serverStart():
            self._reporting.info("Everything seems ok with the X server.",
                    level = PLUGIN, origin = self)
            self._result = ReturnSuccess

        elif not os.path.exists(self.confPath):
            # If the configuration is not there dont even bother to try fixing it.
            # This will go through the proces of trying to fix it.  at least we
            #told the user.
            self._reporting.info("The error is in the xservers autodetection "
                    "mechanism, this does not have an automated solution yet.",
                    level = PLUGIN, origin = self)
            self._result = ReturnFailure

        else:
            self._reporting.info("X server is missconfigured.", level = PLUGIN,
                    origin = self)
            self._result = ReturnFailure
        self._issue.set(checked = True,
                happened = (self._result == ReturnFailure),
                reporting = self._reporting, level = PLUGIN, origin = self)


    def backup(self):
        if os.path.isfile(self.confPath):
            self.backupSpace.backupPath(self.confPath)
        else:
            self._reporting.info("%s does not exist." % self.confPath,
                    level = PLUGIN, origin = self)
        self._result = ReturnSuccess

    def fix(self):
        self._reporting.info("Starting the fix task.", level = PLUGIN,
                origin = self)
        # With the current xorg server the only thing that we need to do is to 
        # erase the conf file.
        if os.path.exists(self.confPath):
            os.remove(self.confPath)

        self._reporting.info("Testing modified environment", level = PLUGIN,
                origin = self)
        if self.serverStart():
            self._reporting.info("X server started successfully with no "
                    "config file.", level = PLUGIN, origin = self)
            self._reporting.info("If you must have a config file, create "
                    "one with system-config-display and place it at "
                    "/etc/X11/xorg.conf", level = PLUGIN, origin = self )
            self._result = ReturnSuccess

            # Lets give the user his previous file.
            if self.backupSpace.exists(path=self.confPath):
                self.backupSpace.restoreName(self.confPath,
                        "%s-FAKbackup"%self.confPath)

        else:
            self._reporting.info("X server is does not autodetect the users "
                    "environment.", level = PLUGIN, origin = self)
            self._result = ReturnFailure

        self._issue.set(fixed = (self._result == ReturnSuccess),
                reporting = self._reporting, level = PLUGIN, origin = self)

    def restore(self):
        if not self.backupSpace.exists(path=self.confPath):
            # This is the case where there is no config file.
            self._reporting.info("The backedup file was not present. Assuming "
                    "that xorg did not have a config file to begin with.", 
                    level = PLUGIN, origin = self)
        else:
            self._reporting.info("Restoring original file.", level = PLUGIN ,
                    origin = self)
            self.backupSpace.restoreName(self.confPath)

        self._result = ReturnSuccess

    def clean(self):
        self._result = ReturnSuccess


    def serverStart(self):
        self._reporting.info("Trying to start X server", level = PLUGIN,
                origin = self)
        xorgargs = [self.display]
        try:
            proc = spawnvch(executable = "/usr/bin/Xorg", args = xorgargs,
                    chroot = Config.system.root)
            self._reporting.info("Waiting for the X server to start...",
                    level = PLUGIN, origin = self)
            time.sleep(5)
            if proc.poll() is not None:
                # process has terminated, failed.
                raise OSError
        except:
            self._reporting.info("The X server has failed to start",
                    level = PLUGIN, origin = self)
            return False
        self._reporting.info("The X server has started successfully",
                level = PLUGIN, origin = self)
        os.kill(proc.pid, signal.SIGINT)
        return True


def get_plugin():
    return Xserver

