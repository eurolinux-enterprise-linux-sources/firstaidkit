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
from pyfirstaidkit.utils import spawnvch
from pyfirstaidkit.configuration import Config
import os, os.path


class Packages(Issue):
    name = "Required Packages database"
    description = "The file containing the rpm database of packages is missing or corrupted"

    def detect(self):
        result = Issue.detect(self)
        if result is not None:
            return result

        dbname = os.path.join(Config.system.root, "/var/lib/rpm/Packages")
        self._happened = False

        if not os.path.isfile(os.path.realpath(dbname)):
            self._db_missing = True
            self._happened = True
            self._checked = True
            return True
        
        #verify the Package database
        rpm_verify = spawnvch(executable = "/usr/lib/rpm/rpmdb_verify", args = ["/usr/lib/rpm/rpmdb_verify", dbname], chroot = Config.system.root)
        err = rpm_verify.wait()
        if err!=0:
            return False

        if len(rpm_verify.stdout.read())>0:
            self._happened = True
        if len(rpm_verify.stderr.read())>0:
            self._happened = True

        self._checked = True
        return True

    def fix(self):
        result = Issue.fix(self)
        if result is not None:
            return result

        dbname = os.path.join(Config.system.root,"/var/lib/rpm/Packages")

        if not self._db_missing:
            #dump&load the database
            os.rename(dbname, dbname+".orig")
            err = spawnvch(executable = "/bin/sh", args = ["sh", "-c", "/usr/lib/rpm/rpmdb_dump /var/lib/rpm/Packages.orig | /usr/lib/rpm/rpmdb_load /var/lib/rpm/Packages"], chroot = Config.system.root).wait()
            if rpm.returncode!=0:
                os.rename(dbname+".orig", dbname)
                return False

        #rebuild the indexes
        rpm = spawnvch(executable = "/bin/rpm", args = ["rpm", "--rebuilddb"], chroot = Config.system.root).wait()
        if rpm.returncode==0:
            self._fixed = True
        return True

