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

from pyfirstaidkit.plugins import Plugin,Flow
from pyfirstaidkit.reporting import PLUGIN
from pyfirstaidkit.returns import *
from pyfirstaidkit.issue import SimpleIssue

class Sample1Plugin(Plugin):
    """This plugin uses the predefined flow in the Plugin abstract class."""
    name = "Sample1Plugin"
    version = "0.0.1"
    author = "Joel Andres Granados"
    def __init__(self, *args, **kwargs):
        Plugin.__init__(self, *args, **kwargs)
        self._issue = SimpleIssue(self.name, self.description)

    def prepare(self):
        self._result=ReturnSuccess
        self._issue.set(reporting  = self._reporting, origin = self, level = PLUGIN)
        self._backup = self._backups.getBackup(self.__class__.__name__+" -- "+self.name, persistent = True)
        self._reporting.info("Sample1Plugin in Prepare task", origin = self, level = PLUGIN)

    def backup(self):
        self._result=ReturnSuccess
        self._reporting.info("Sample1Plugin in backup task", origin = self, level = PLUGIN)

    def restore(self):
        self._result=ReturnSuccess
        self._reporting.info("Sample1Plugin in Restore task", origin = self, level = PLUGIN)

    def diagnose(self):
        self._result=ReturnSuccess
        self._issue.set(checked = True, happened = False, reporting  = self._reporting, origin = self, level = PLUGIN)
        self._reporting.info("Sample1Plugin in diagnose task", origin = self, level = PLUGIN)

    def fix(self):
        self._result=ReturnFailure
        self._issue.set(fixed = False, reporting  = self._reporting, origin = self, level = PLUGIN)
        self._reporting.info("Sample1Plugin in Fix task", origin = self, level = PLUGIN)

    def clean(self):
        self._result=ReturnSuccess
        self._backups.closeBackup(self._backup._id)
        self._reporting.info("Sample1Plugin in Clean task", origin = self, level = PLUGIN)

def get_plugin():
    return Sample1Plugin
