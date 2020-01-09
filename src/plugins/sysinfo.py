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
from pyfirstaidkit.configuration import Config
from pyfirstaidkit.utils import spawnvch

import os

class Sample1Plugin(Plugin):
    """Discover information about the system"""
    name = "Discovery"
    description = "Discover properties of the system"
    version = "0.0.1"
    author = "Martin Sivak"

    flows = Flow.init(Plugin)
    flows["fix"] = flows["diagnose"]

    def __init__(self, *args, **kwargs):
        Plugin.__init__(self, *args, **kwargs)
        self._issue = SimpleIssue(self.name, "Discovering system properties failed")

    def prepare(self):
        self._issue.set(reporting  = self._reporting, origin = self, level = PLUGIN)
        self._result=ReturnSuccess

    def diagnose(self):
        #architecture and cpus
        (unamestdout, unamestderr) = spawnvch(executable = "/bin/uname", args = ["uname", "-a"], chroot = Config.system.root).communicate("")
        self._info.uname = unamestdout.split("\n")[0]

        #memory
        (freestdout, freestderr) = spawnvch(executable = "/usr/bin/free", args = ["free"], chroot = Config.system.root).communicate("")
        freedata = freestdout.split("\n")
        self._info.memory = freedata[1].split()[1]
        self._info.swap = freedata[3].split()[1]

        #pci
        pcilist = []
        (lspcistdout, lspcistderr) = spawnvch(executable = "/sbin/lspci", args = ["lspci"], chroot = Config.system.root).communicate("")
        for l in lspcistdout.split("\n"):
            try:
                (id, name) = l.split(" ", 1)
                setattr(self._info, "_".join(["pci", id]), name)
                pcilist.append(id)
            except:
                pass
        self._info.pci = " ".join(pcilist)

        #usb
        if os.path.exists(os.path.join(Config.system.root, "/proc/bus/usb")):
            self._info.usb = "True"
        else:
            self._info.usb = "False"

        #scsi
        if os.path.exists(os.path.join(Config.system.root, "/proc/scsi/device_info")):
            self._info.scsi = "True"
        else:
            self._info.scsi = "False"

        #ide
        if os.path.exists(os.path.join(Config.system.root, "/proc/ide")):
            self._info.ide = "True"
        else:
            self._info.ide = "False"

        #partitions
        partitionlist = []
        for l in open("/proc/partitions").readlines()[2:]:
            try:
                (major, minor, blocks, name) = l.split()
                if name.startswith("ram"):
                    continue
                setattr(self._info, "_".join(["partition", name]), blocks)
                partitionlist.append(name)
            except:
                continue
        self._info.partition = " ".join(partitionlist)

        #net


        self._dependencies.provide("discovery")
        self._issue.set(checked = True, happened = False, reporting  = self._reporting, origin = self, level = PLUGIN)
        self._result=ReturnSuccess

    def clean(self):
        self._result=ReturnSuccess

def get_plugin():
    return Sample1Plugin
