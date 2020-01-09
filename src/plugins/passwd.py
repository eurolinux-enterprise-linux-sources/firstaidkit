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
from pyfirstaidkit.utils import *
from pyfirstaidkit.reporting import PLUGIN
from pyfirstaidkit import Config
from random import Random

rng = Random()

class PasswdPlugin(Plugin):
    """This plugin provides operations for convenient manipulation with the
    password system."""
    #
    # Additional flow defprepareion.
    #
    # flows = Flow.init(Plugin) # we do not need the default fix and diagnose
    # flows
    flows = {}
    flows["resetRoot"] = Flow({
                    Plugin.initial: {Return: "resetRoot"},
                    "resetRoot"     : {ReturnSuccess: Plugin.final}
                    }, description="Reset root password to random value so " \
                            "the user can login and change it")

    name = "Password plugin"
    version = "0.0.1"
    author = "Martin Sivak"
    description = "Automates the recovery of the root system passwd"

    @classmethod
    def getDeps(cls):
        return set(["root", "filesystem"])

    def __init__(self, *args, **kwargs):
        Plugin.__init__(self, *args, **kwargs)

    def resetRoot(self):
        charlist = "abcdefghijklmnopqrstuvwxyz" \
                "1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ.,"
        passlen = 10
        newpasswd = []
        while len(newpasswd)<passlen:
            newpasswd.append(rng.choice(charlist))

        print spawnvch(executable = "/usr/bin/passwd",
                args = ["/usr/bin/passwd", "root"],
                chroot = Config.system.root).communicate(
                        input = "%s\n%s\n"%(newpasswd,newpasswd))

        self._reporting.info("Root password was reset to '%s'" % 
                ("".join(newpasswd),), level = PLUGIN, origin = self)

        self._result=ReturnSuccess

def get_plugin():
    return PasswdPlugin
