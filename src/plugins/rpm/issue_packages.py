# File name: issue_filesystem.py
# Date:      2008/03/14
# Author:    Martin Sivak <msivak at redhat dot com>
#
# Copyright (C) Red Hat 2008
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# in a file called COPYING along with this program; if not, write to
# the Free Software Foundation, Inc., 675 Mass Ave, Cambridge, MA
# 02139, USA.

from pyfirstaidkit.issue import Issue
from pyfirstaidkit.reporting import TASK

class RequiredPackages(Issue):
    name = "Required Packages"
    description = "There are some very important packages missing. It is likely your instalation could be damaged."

    packages_list = ["filesystem", "initscripts", "glibc", "kernel", "bash", "module-init-tools"]

    def detect(self):
        result = Issue.detect(self)
        if result is not None:
            return result

        architectures = {}

        for p in self.packages_list:
            architectures[p] = set()
            mi=self._plugin.rpm.dbMatch("name", p)
            for hdr in mi:
                self._plugin._reporting.debug(level = TASK, origin = self, message = "Found package %s with architecture %s" % (p, hdr["arch"]))
                architectures[p].add(hdr["arch"])

        #is there a common architecture for all the packages?
        all = reduce(lambda acc,x: acc.union(x), architectures.values(), set())
        common = reduce(lambda acc,x: acc.intersection(x), architectures.values(), all)
        self._plugin._reporting.debug(level = TASK, origin = self, message = "Common architecture for all packages is %s" % ("+".join(common),))

        if len(common)==0:
            self._happened = True
        else:
            self._happened = False

        self._checked = True
        return True

    def fix(self):
        result = Issue.fix(self)
        if result is not None:
            return result

        yum = spawnvch(executable = "/usr/bin/yum", args = ["yum", "install"] + packages_list, chroot = Config.system.root).communicate("y\ny\n")
        if yum.returncode==0:
            self._fixed = True

        return True
