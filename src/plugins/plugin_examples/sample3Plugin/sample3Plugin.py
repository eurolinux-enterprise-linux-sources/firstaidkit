# First Aid Kit - diagnostic and repair tool for Linux
# Copyright (C) 2007 Martin Sivak <msivak@redhat.com>
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

from pyfirstaidkit.returns import *
from pyfirstaidkit.plugins import Plugin,Flow
from pyfirstaidkit import Config
from pyfirstaidkit.issue import SimpleIssue
from pyfirstaidkit.reporting import PLUGIN
import subprocess

class Sample3Plugin(Plugin):
    """This plugin will use a shell script as backend."""
    name = "Sample3Plugin"
    version = "0.0.1"
    author = "Joel Andres Granados"

    def __init__(self, *args, **kwargs):
        Plugin.__init__(self,  *args, **kwargs)
        self._issue = SimpleIssue(self.name, self.description)

    def prepare(self):
        # Prepare command line.
        self._issue.set(checked = False, reporting  = self._reporting, origin = self, level = PLUGIN)
        prepare = [self._path + "/plugin", "--task", "prepare"]
        proc = subprocess.Popen(prepare, stdout=subprocess.PIPE)
        (out, err) = proc.communicate()
        out = out.strip()
        if out[-5:] == "false":
            self._result=ReturnFailure
        elif out[-4:] == "true":
            self._result=ReturnSuccess

    def clean(self):
        clean = [self._path+"/plugin", "--task", "clean"]
        proc = subprocess.Popen(clean, stdout=subprocess.PIPE)
        (out, err) = proc.communicate()
        out = out.strip()
        if out[-5:] == "false":
            self._result=ReturnFailure
        elif out[-4:] == "true":
            self._result=ReturnSuccess

    def backup(self):
        backup = [self._path+"/plugin", "--task", "backup"]
        proc = subprocess.Popen(backup, stdout=subprocess.PIPE)
        (out, err) = proc.communicate()
        out = out.strip()
        if out[-5:] == "false":
            self._result=ReturnFailure
        elif out[-4:] == "true":
            self._result=ReturnSuccess

    def restore(self):
        restore = [self._path+"/plugin", "--task", "restore"]
        proc = subprocess.Popen(restore, stdout=subprocess.PIPE)
        (out, err) = proc.communicate()
        out = out.strip()
        if out[-5:] == "false":
            self._result=ReturnFailure
        elif out[-4:] == "true":
            self._result=ReturnSuccess

    def diagnose(self):
        diagnose = [self._path+"/plugin", "--task", "diagnose"]
        proc = subprocess.Popen(diagnose, stdout=subprocess.PIPE)
        (out, err) = proc.communicate()
        out = out.strip()
        if out[-5:] == "false":
            self._result=ReturnFailure
        elif out[-4:] == "true":
            self._result=ReturnSuccess
        self._issue.set(checked = True, happened = (self._result==ReturnFailure), reporting  = self._reporting, origin = self, level = PLUGIN)

    def fix(self):
        fix = [self._path+"/plugin", "--task", "fix"]
        proc = subprocess.Popen(fix, stdout=subprocess.PIPE)
        (out, err) = proc.communicate()
        out = out.strip()
        if out[-5:] == "false":
            self._result=ReturnFailure
        elif out[-4:] == "true":
            self._result=ReturnSuccess
        self._issue.set(fixed = (self._result==ReturnSuccess), reporting  = self._reporting, origin = self, level = PLUGIN)

