# First Aid Kit - diagnostic and repair tool for Linux
# Copyright (C) 2008 Joel Andres Granados <jgranado@redhat.com>
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
from pyfirstaidkit.reporting import PLUGIN
import signal
import _undelpart

class UndeletePartition(Plugin):
    """Plugin to detect and correct deleted partitions from system disks.

    Uses parted libriary to search for partitions that are not included in
    the partition table of a disk.  If it is possible, this plugin will put
    the partition back into the parition table so it is visible to the
    system again.
    """

    flows = Flow.init(Plugin)
    # We have not restore in the noBackup flow because we have no information to restore with.
    flows["noBackup"] = Flow({
                    Plugin.initial: {Return: "prepare"},
                    "prepare"     : {ReturnSuccess: "diagnose"},
                    "diagnose"    : {ReturnSuccess: "clean", ReturnFailure: "fix"},
                    "fix"         : {ReturnSuccess: "clean", ReturnFailure: "clean"},
                    "clean"       : {ReturnSuccess: Plugin.final}
                    }, description="This flow skips the backup test.  Use with care.")

    name = "Undelete Partitions"
    version = "0.1.0"
    author = "Joel Andres Granados"
    def __init__(self, *args, **kwargs):
        Plugin.__init__(self, *args, **kwargs)

        # Dictionary that will hold the partitions that are not included in the
        # partition table of a certain disk and can be recovered. It will also
        # house the initial partition table and the partition table that is a
        # result of running the fix.  The structure is:
        # slef.disks={diskname: [ [recoverables], initialPT, finalPT ], .... }
        self.disks = {}

    def prepare(self):
        # For now there is no real action in the prepare task.
        self._result=ReturnSuccess

    #
    # The diagnose will not be a real diagnose but more of an informative task.
    # It will report all the possible paritions that could house a rescuable
    # partition.
    #
    def diagnose(self):
        self._reporting.info("Beginning Diagnose...", origin = self, level = PLUGIN)
        self.disks = _undelpart.getDiskList()
        self._reporting.info("Disks present in the system %s"%self.disks.keys(),
                origin = self, level = PLUGIN)
        # When we find a rescuable partition we change this to true.
        rescuablePresent = False
        for disk, elements in self.disks.iteritems():
            self.disks[disk] = [ _undelpart.getRescuable(disk), _undelpart.getPartitionList(disk), [] ]
            if len(self.disks[disk][0]) > 0:
                self._reporting.info("Possible partitions to recover in disk %s: %s"%(disk, self.disks[disk][0]),
                        origin = self, level = PLUGIN)
                rescuablePresent = True
        if not rescuablePresent:
            self._result = ReturnSuccess
            self._reporting.info("Did not find any partitions that need rescueing.",
                    origin = self, level = PLUGIN)
        else:
            self._result = ReturnFailure

    def backup(self):
        self._reporting.info("Backing up partition table." , origin = self, level = PLUGIN)
        # We actually already have the backup of the partition table in the self.disks dict.
        # Lets check anyway.
        backupSane = True
        for disk, members in self.disks.iteritems():
            if members[1] == None or len(members[1]) <= 0:
                # We don't really have the partition table backup.
                self._reporting.info("Couldn't backup the partition table for %s."%disk,
                        origin = self, level = PLUGIN)
                self._reporting.info("To force the recovery of this disk without the backup " \
                    "please run the flow named noBackup from this plugin.",
                    origin = self, level = PLUGIN)
                backupSane = False
                self._result = ReturnFailure

        if backupSane:
            self._result = ReturnSuccess

    #
    # Every partition that we suspect is rescuable, (given that it has a partition table from
    # wich we can recover if we mess up) we try to rescue.  This will take a long time.
    #
    def fix(self):
        self._reporting.info("Lets see if I can fix this... Starting fix task.",
                origin = self, level = PLUGIN)
        self._reporting.info("Might want to go and get a cup of coffee,"
                "this could take a looooooong time...", origin = self, level = PLUGIN)
        self._result = ReturnSuccess
        rescued = []
        try:
            for disk, members in self.disks.iteritems():
                if len(members[0]) > 0:#there are partitions to rescue :)
                    self._reporting.info("Trying to rescue %s from disk %s"%(members[0], disk),
                            origin = self, level = PLUGIN)
                    rescued = _undelpart.rescue(disk,members[0])
                    self._reporting.info("Partitions rescued: %s"%rescued,
                            origin = self, level = PLUGIN)
                elif len(members[0]) ==  0:
                    self._reporting.info("Nothing to rescue on disk %s."%disk,
                            origin = self, level = PLUGIN)
                else:
                    self_result = ReturnFailure
                    break
        except KeyboardInterrupt, e:
            self._reporting.error("Received a user interruption... Moving to Restore task.",
                    origin = self, level = PLUGIN, action = None)
            # The user might want to keep on pushing ctrl-c, lets lock the SIGINT signal.
            signal.signal(signal.SIGINT, keyboaordInterruptHandler)
            self._reporting.info("Please wait until the original partition table is recovered.",
                    origin = self, level = PLUGIN)
            self._result = ReturnFailure

    #
    # We are not really erasing anything, so recovering is kinda out of the point.  That said
    # anything can happen with partitioning. :)  Lets get the current partitionList and try
    # to add all the partitions that are not in the current part list but are in the backedup
    # one.
    #
    def restore(self):
        self._reporting.info("Starting Restoring task." , origin = self, level = PLUGIN)
        tempPartList = []
        backupPartList = []
        for disk, members in self.disk.iteritems():
            tempPartList = _undelpart.getPartitionList(disk)
            backupPartList = members[1]
            for part in backupPartList:
                if part not in tempPartList:# we need to restore
                    self._reporting.info("Trying to restore partition %s on disk %s"%(part, disk),
                            origin = self, level = PLUGIN)
                    restore = _undelpart.rescue(disk, [part])
                    if len(restore) > 0:
                        self._reporting.info("Restored partition %s on disk %s"%(part, disk),
                                origin = self, level = PLUGIN)
                    else:
                        self._reporting.error("Could not restore partititon %s on disk %s"%(part, disk),
                                origin = self, level = PLUGIN, action = None)
        # Return the signal to its previous state.
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        self._result = ReturnSuccess

    def clean(self):
        self._reporting.info("Cleanning...",origin = self, level = PLUGIN)
        self._result = ReturnSuccess

def keyboardInterruptHandler(signum, frame):
    pass
