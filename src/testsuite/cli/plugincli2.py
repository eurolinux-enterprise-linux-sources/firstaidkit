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

class Plugincli2(Plugin):
    name = "Plugincli2"
    version = "3.4.5"
    author = "John Galt"

    def __init__(self, *args, **kwargs):
        Plugin.__init__(self, *args, **kwargs)
        self._reporting.info("Entering the init phase...", origin = self)

    def prepare(self):
        self._reporting.info("Entering the prepare phase...", origin = self)
        self._result = ReturnSuccess

    def backup(self):
        self._reporting.info("Entering the backup phase...", origin = self)
        self._result = ReturnSuccess

    def restore(self):
        self._reporting.info("Entering the restore phase...", origin = self)
        self._result = ReturnSuccess

    def diagnose(self):
        self._reporting.info("Entering the diagnose phase...", origin = self)
        self._result = ReturnSuccess

    def fix(self):
        self._reporting.info("Entering the fix phase...", origin = self)
        self._result = ReturnSuccess

    def clean(self):
        self._reporting.info("Entering the clean phase...", origin = self)
        self._result = ReturnSuccess

def get_plugin():
    return Plugincli2
