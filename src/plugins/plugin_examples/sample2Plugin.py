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
from pyfirstaidkit.returns import *
from pyfirstaidkit.issue import SimpleIssue
from pyfirstaidkit.reporting import PLUGIN

class Sample2Plugin(Plugin):
    """This plugin will defin one more function and use it in a newly defined fix flow."""
    #
    # Additional flow defprepareion.
    #
    flows = Flow.init(Plugin)
    flows["fix"] = Flow({
                    Plugin.initial: {Return: "prepare"},
                    "prepare"     : {ReturnSuccess: "diagnose"},
                    "diagnose"    : {ReturnSuccess: "clean", ReturnFailure: "backup"},
                    "backup"      : {ReturnSuccess: "fix", ReturnFailure: "clean"},
                    "restore"     : {ReturnSuccess: "clean", ReturnFailure: "clean"},
                    "fix"         : {ReturnSuccess: "extraStep", ReturnFailure: "restore"},
                    "extraStep"   : {ReturnSuccess: "clean", ReturnFailure: "clean"},
                    "clean"       : {ReturnSuccess: Plugin.final}
                    }, description="Fixing sequence with one added extraStep")

    name = "Sample2Plugin"
    version = "0.0.1"
    author = "Joel Andres Granados"

    def __init__(self, *args, **kwargs):
        Plugin.__init__(self, *args, **kwargs)
        self._issue = SimpleIssue(self.name, self.description)

    def prepare(self):
        self._issue.set(reporting  = self._reporting, origin = self, level = PLUGIN)
        self._result=ReturnSuccess

    def clean(self):
        self._result=ReturnSuccess

    def backup(self):
        self._result=ReturnSuccess

    def restore(self):
        self._result=ReturnSuccess

    def diagnose(self):
        self._issue.set(checked = True, happened = True, reporting  = self._reporting, origin = self, level = PLUGIN)
        self._result=ReturnFailure

    def fix(self):
        self._issue.set(fixed = True, reporting  = self._reporting, origin = self, level = PLUGIN)
        self._result=ReturnSuccess

    def extraStep(self):
        self._result=ReturnSuccess

def get_plugin():
    return Sample2Plugin
