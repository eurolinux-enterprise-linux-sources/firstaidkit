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
from pyfirstaidkit.configuration import Config
from pyfirstaidkit.reporting import PLUGIN
from pyfirstaidkit.returns import *
from pyfirstaidkit.issue import SimpleIssue
from pyfirstaidkit.utils import spawnvch
import os
import re

class mkinitrd(Plugin):
    """This plugin uses the predefined flow in the Plugin abstract class."""
    name = "mkinitrd"
    version = "0.0.1"
    author = "Adam Pribyl"

    flows = Flow.init(Plugin)
    flows["mkinitrd"] = flows["fix"]
    del flows["fix"]
    del flows["diagnose"]                

    @classmethod
    def getDeps(cls):
        return set(["root"]).union(Plugin.getDeps())

    def __init__(self, *args, **kwargs):
        Plugin.__init__(self, *args, **kwargs)
        self._issue = SimpleIssue(self.name, self.description)
        self.initrd = None #
        self.initrd_path = None
        self.kernel_version = None
        self.kernel_re = re.compile(".*initrd-(?P<kernel>.*)\.img")
        self.initrds = [] # array of intirds found ing menu.lst

    def prepare(self):
        self._issue.set(reporting  = self._reporting, origin = self, level = PLUGIN)
        self._backup = self._backups.getBackup(self.__class__.__name__+" -- "+self.name, persistent = False)
        self._reporting.info("mkinitrd in Prepare task", origin = self, level = PLUGIN)
        f = open(os.path.join(Config.system.root,"/boot/grub/menu.lst"))
        for l in f:
          ltmp = l.strip()
          self._reporting.debug("parsing line: %s"%ltmp, origin = self, level = PLUGIN)
          if ltmp.startswith("default"):
            self.initrd = int(ltmp[8:])
            self._reporting.debug("found default: %d"%self.initrd, origin = self, level = PLUGIN)
          elif ltmp.startswith("initrd"):
            self.initrds.append(ltmp.split()[1][1:])
            self._reporting.debug("found initrd: %s"%self.initrds[-1], origin = self, level = PLUGIN)            

        self._reporting.debug("config root: %s"%Config.system.root, origin = self, level = PLUGIN)
        self._reporting.debug("looking for: %s"%os.path.join(Config.system.root,self.initrds[self.initrd]), origin = self, level = PLUGIN)
        self._reporting.debug("looking for: %s"%os.path.join(Config.system.root,"boot",self.initrds[self.initrd]), origin = self, level = PLUGIN)
        if os.path.exists(os.path.join(Config.system.root,self.initrds[self.initrd])):
          self.initrd_path = os.path.join(Config.system.root,self.initrds[self.initrd]) 
        elif os.path.exists(os.path.join(Config.system.root,"boot",self.initrds[self.initrd])):
          self.initrd_path = os.path.join(Config.system.root,"boot",self.initrds[self.initrd])
        else:
          self.result=ReturnFailure
          self._reporting.error("initrd not found", origin = self, level = PLUGIN)
          return
        
        self._reporting.info("initrd found: %s"%(self.initrd_path,), origin = self, level = PLUGIN) 
        m = self.kernel_re.match(self.initrds[self.initrd])
        if not m :
          self._reporting.error("kernel version not identified", origin = self, level = PLUGIN)
          self._result=ReturnFailure
          return
          
        self.kernel_version = m.group("kernel")
        self._reporting.info("kernel version: %s"%(self.kernel_version,), origin = self, level = PLUGIN) 
        self._result=ReturnSuccess

    def backup(self):
        self._reporting.info("mkinitrd in backup task", origin = self, level = PLUGIN)
        self._backup.backupPath(self.initrd_path)
        self._result=ReturnSuccess

    def restore(self):
        self._reporting.info("mkinitrd in Restore task", origin = self, level = PLUGIN)
        self._backup.restorePath(self.initrd_path)
        self._result=ReturnSuccess
        
    def diagnose(self):
        self._result=ReturnFailure
        self._issue.set(checked = True, happened = True, reporting  = self._reporting, origin = self, level = PLUGIN)
        self._reporting.info("mkinitrd in diagnose task", origin = self, level = PLUGIN)

    def fix(self):
        self._issue.set(fixed = False, reporting  = self._reporting, origin = self, level = PLUGIN)
        self._reporting.info("mkinitrd in Fix task", origin = self, level = PLUGIN)
        print spawnvch("/sbin/mkinitrd", ["mkinitrd", self.initrd_path[len(Config.system.root):],self.kernel_version], Config.system.root).communicate()
        self._result=ReturnFailure

    def clean(self):
        self._result=ReturnSuccess
        self._backups.closeBackup(self._backup._id)
        self._reporting.info("mkinitrd in Clean task", origin = self, level = PLUGIN)

def get_plugin():
    return mkinitrd
