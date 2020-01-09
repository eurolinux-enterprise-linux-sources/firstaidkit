# First Aid Kit - diagnostic and repair tool for Linux
# Copyright (C) 2008 Joel Granados <jgranado@redhat.com>
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

from pyfirstaidkit.plugins import Plugin, Flow
from pyfirstaidkit.returns import *

class PluginInfo(Plugin):
    name = "TestInfoPlugin"
    version = "3.4.5"
    author = "John Galt"
    flows={}
    flows["newflow"] = Flow({
            Plugin.initial: {Return: "prepare"},
            "prepare"     : {ReturnSuccess: "fix"},
            "fix"         : {ReturnSuccess: "clean", ReturnFailure: "clean"},
            "clean"       : {ReturnSuccess: Plugin.final}
            }, description="This is the newflow")

    def __init__(self, *args, **kwargs):
        Plugin.__init__(self, *args, **kwargs)

    def prepare(self):
        pass

    def backup(self):
        pass

    def restore(self):
        pass

    def diagnose(self):
        pass

    def fix(self):
        pass

    def clean(self):
        pass

def get_plugin():
    return PluginInfo
