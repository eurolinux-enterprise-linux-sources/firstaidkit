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
from pyfirstaidkit.utils import *
from pyfirstaidkit.reporting import PLUGIN
from pyfirstaidkit.issue import SimpleIssue
from pyfirstaidkit import Config
from pyfirstaidkit.errors import *

from grubUtils import Dname
import grubUtils

import os

class Grub(Plugin):
    """Plugin to detect and fix grub failure."""
    flows = Flow.init(Plugin)
    name = "Grub"
    version = "0.0.1"
    author = "Joel Andres Granados"
    description = "Plugin to recover lost grub bootloader functionality"

    @classmethod
    def getDeps(cls):
        return set(["root", "filesystem"])

    @classmethod
    def revert(cls, backup, report):
        """ Use the backup object to replace the first 446 bytes in all devs.
        """
        report.info("Entering revert...", origin = Grub)
        try:
            firstblockdict = backup.restoreValue("firstblockdict")
        except:
            report.debug("I found the grub backup dir empty", origin = Grub)
            return

        if len(firstblockdict) == 0:
            report.info("I found a backup object but it had no elements to " \
                    "backup, exiting...", origin = Grub)
            return

        for (dev, val) in firstblockdict.iteritems():
            devpath = val[1].path()
            first446bytes = val[0]
            report.info("Reverting changes for device %s." % devpath, \
                    origin = Grub)
            try:
                fd = os.open(devpath, os.O_WRONLY)
                os.write(fd, first446bytes)
                os.close(fd)
            except IOError, ie:
                report.debug("There was an error writing to %s, It is very " \
                        "probable that this device is in an invalid state." \
                        "Error: %s" % (devpath, ie), origin = Grub)
            except Exception, e:
                report.debug("There was an unexpected error: %s" % e, \
                        origin = Grub)

            report.info("Successfully reverted changes to device %s." % devpath, \
                    origin = Grub)

    def __init__(self, *args, **kwargs):
        Plugin.__init__(self, *args, **kwargs)

        # The key is a dev name, the value is a list of partitions in drive.
        self.devices = {}

        # The partitions where the grub directory and all the necessary files
        # found.
        self.grub_dir_parts = []

        # The partitions where grub binary will be installed (first 446 bytes).
        self.install_grub_parts = []

        # The devs where grub binary will be installed (first 446 bytes).
        self.install_grub_devs = []

        # Initialize our list of related issues.
        self.issue_grub_dir = SimpleIssue(self.name+"_DIR", "Missing grub " \
                "dir or dir files.")
        self.issue_grub_image = SimpleIssue(self.name+"_IMAGE", "Bad grub " \
                "stage1 image.")

        # Initialize the backup space.
        self.backupSpace = self._backups.getBackup( \
                self.__module__.split('.')[-1:][0], persistent = True)

        # Parce the parameters passed to the plugin.
        self.args = grubUtils.get_grub_opts(self._args)

        # Place where the grub files, kernel and initrd files are.
        self.grubroot = None

    def prepare(self):
        self._reporting.info("Initializing the search for all the grub " \
                "related elements.", origin = self)

        try:
            # We end up with a structure where the keys are the drive names.
            self.devices = grubUtils.get_all_devs()

            # We must search in all the possible partitions for the grub files:
            # stage1, stage1.5, stage2....  When we find these directories we
            # will be able to install grub from there.  And the vmliuz (kernel
            # image), initrd.img, the grub.conf is probably in these places as
            # well.
            self._reporting.info("Searching for grub related files in the " \
                    "system storage devices.", origin = self)
            for (dev, parts) in self.devices.iteritems():
                for part in parts:
                    try:
                        if grubUtils.grub_dir_in_partition(part):
                            self._reporting.info("Found grub dir in %s " \
                                    "partition." % part.path(), origin = self)
                            self.grub_dir_parts.append(part)
                    except Exception, e:
                        # If something happened while checking the partition
                        # it will not be taken into account.
                        self._reporting.error("There was an error while " \
                                "searching partition %s. Error: %s." % \
                                (part.path(), e) ,origin = self)

            # Out of all the dirs we found we select one.
            # FIXME: extend the grub root concept so it can handle varous roots in
            #        a system.  For now we just select the first and hope it has
            #        everything.
            self.grubroot = grubUtils.find_grub_root(self.grub_dir_parts)

            # We decide to which devices the grub image will be installed.
            # 1. If no arguments were passed, then no installation is done.
            # 2. If the list of devices was passes we use that.
            # 3. if the install_auto arg was passes we install were we dont
            #    break anything.
            # 4. If the install_all is passed we install in every device and
            #    partition.
            #
            self._reporting.info("Searching for locations in which to " \
                    "install grub.", origin = self)

            if len(self.args.installto_devs)+len(self.args.installto_parts) > 0:
                # We install to the selected devices.  Since grub-install
                # will screat in case the device names are not valid, I think
                # its not necesary to check here.
                for dev in self.args.installto_devs:
                    self.install_grub_devs.append(Dname(dev))

                for part in self.args.installto_parts:
                    self.install_grub_parts.append(Dname(part))

            elif self.args.install_all:
                # We install to all the devices
                for (dev, parts) in self.devices.iteritems():
                    self.install_grub_devs.append(Dname(dev))
                    for part in parts:
                        self.install_grub_parts.append(Dname(part))

            elif self.args.install_auto:
                # Skip devices with other bootloader (default).
                for (dev, parts) in self.devices.iteritems():

                    # We see if we can install grub in device.
                    # FIXME: Create exception for failed bootloader search.
                    if not grubUtils.other_bootloader_present(Dname(dev)):
                        self._reporting.info("Found no other bootloader in " \
                                "%s device." % Dname.asPath(dev), \
                                origin = self)
                        self.install_grub_devs.append(Dname(dev))

                    # Now we see if we can install in the partitions.
                    for part in parts:
                        if not grubUtils.other_bootloader_present(Dname(part)):
                            self._reporting.info("Found no other bootloader " \
                                    "in %s partition." % Dname.asPath(part), \
                                    origin = self)
                            self.install_grub_parts.append(Dname(part))
            else:
                # If not arguments where specified the right thing to do is to
                # leave everything alone:)
                self.install_grub_parts = []
                self.install_grub_devs = []
                self._reporting.info("Grub wont modify any drive. " \
                        "If you want grub to take action you must specify: " \
                        "--installto-devs, --installto-parts, " \
                        "--install-all or --install-auto.", \
                        origin = self)

            self._result = ReturnSuccess
        except Exception, e:
            self._reporting.error("An error has ocurred while searching for " \
                    "grubs elements.  Error: %s" % e, origin = self)
            self._result = ReturnFailure

    def diagnose(self):
        # FIXME ATM we will not take care of the cases that are missing some
        # stuff from the grub directory, like images and conffile.
        #
        # The diagnose is tricky because we have no way of knowing (yet) if
        # the images found in the devices actually map correctly to the stuff
        # that we found on the directories.  This means that we will allways
        # reinstall grub in the mbr (the changes will be revertable so its
        # not that bad) unless we don't find any grub dir.  If no dir is
        # found, then we fail (fail in this case means postponing the decision
        # until the fix step to actually ReturnFailure)
        self._reporting.info("Diagnosing the current state of grub.",
                origin = self)
        if len(self.grub_dir_parts) < 0:
            self._reporting.error("No grub directories where found.",
                    origin = self)

            self.issue_grub_dir.set(checked = True, happened = True,
                    reporting = self._reporting, origin = self)
            self.issue_grub_image.set(checked = False,
                    reporting = self._reporting, origin = self)

            self._result = ReturnFailure
            return
        self.issue_grub_dir.set(checked = True, happened = False,
                reporting = self._reporting, origin = self)

        if len(self.install_grub_devs) + len(self.install_grub_parts) == 0:
            # Since we dont check the validity of the images in the mbr we
            # consider all the drives to be in a faulty state
            # FIXME: this defenetly has to change
            self.issue_grub_image.set(checked = True, happened = True, \
                    reporting = self._reporting, origin = self)
        else:
            self.issue_grub_image.set(checked = False, happened = False, \
                    reporting = self._reporting, origin = self)

        self._result = ReturnFailure


    def  backup(self):
        # The grub process is related to the 446 firsta bytes of the partitions
        # of the device.  This means we must backup all the beginings fo the
        # partitions and devices that we will possibly modify.

        # Since we are going to install the stage1 grub image in all the
        # devices in self.install_grub_devs, we will backup all of them.
        # FIXME: We have to modify the plugin to consider partitions.
        firstblockdict = {}

        if len(self.install_grub_devs) > 0:
            self._reporting.info("Going to backup all the first 446 bytes of " \
                    "%s." % self.install_grub_devs, origin = self)
        for device in self.install_grub_devs:
            fd = os.open(device.path(), os.O_RDONLY)
            first446btemp = os.read(fd, 446)
            os.close(fd)
            firstblockdict[device.name()] = [first446btemp, device]

        if len(self.install_grub_parts) > 0:
            self._reporting.info("Going to backup all the first 446 bytes of " \
                    "%s." % self.install_grub_parts, origin = self)
        for part in self.install_grub_parts:
            fd = os.open(part.path(), os.O_RDONLY)
            first446btemp = os.read(fd, 446)
            os.close(fd)
            firstblockdict[part.name()] = [first446btemp, part]

        self.backupSpace.backupValue( firstblockdict, "firstblockdict")
        self._result = ReturnSuccess

    def fix(self):
        # We are to fail if there are no dirs.
        if len(self.grub_dir_parts) == 0:
            self._reporting.error("No grub directories where found... exiting.",
                    origin = self)
            self.issue_grub_dir.set(fixed = False, \
                    reporting = self._reporting, origin = self)
            self._result = ReturnFailure
            return

        # We are to fail if there are no devs or parts to install to.
        if len(self.install_grub_devs) + len(self.install_grub_parts) == 0:
            self._reporting.error("No devices or partitions to install to.",
                    origin = self)
            self.issue_grub_image.set(fixed = False, \
                    reporting = self._reporting, origin = self)
            self._result = ReturnFailure
            return

        # Install the grub in all devs pointing at the special root part.
        for drive in self.install_grub_devs:
            self._reporting.info("Trying to install grub on drive %s, " \
                    "pointing to grub directory in %s."%(drive.path(), \
                    self.grubroot.path()), origin = self)
            try:
                grubUtils.install_grub(self.grubroot, drive)
            except Exception, e:
                self._reporting.error("Grub installation on drive %s, " \
                        "pointing to grub directory in %s has failed." % \
                        (drive.path(), self.grubroot.path()), \
                        origin = self)
                # If one installation fails its safer to just restore
                # everything
                self._result = ReturnFailure
                return

        for part in self.install_grub_parts:
            self._reporting.info("Trying to install grub on part %s, " \
                    "pointing to grub directory in %s." % (part.path(), \
                    self.grubroot.path()), origin = self)
            try:
                grubUtils.install_grub(self.grubroot, part)
            except:
                self._reporting.error("Grub installation on part %s, " \
                        "pointing to grub directory in %s has failed." % \
                        (part.path(), self.grubroot.path()), \
                        origin = self)
                self._result = ReturnFailure
                return

        self.issue_grub_image.set(fixed = True, reporting = self._reporting, \
                origin = self)
        self._reporting.info("Grub has successfully installed in all the " \
                "chosen devices.", origin = self)
        self._result = ReturnSuccess

    def restore(self):
        firstblockdict = self.backupSpace.restoreValue("firstblockdict")
        for (dev, val) in firstblockdict.iteritems():
            devpath = val[1].path()
            first446bytes = val[0]
            self._reporting.info("Restoring changes for device %s." % devpath, \
                    origin = self)
            try:
                fd = os.open(devpath, os.O_WRONLY)
                os.write(fd, first446bytes)
                os.close(fd)
            except IOError, ie:
                self._reporting.debug("There was an error writing to %s, It " \
                        " is very probable that this device is in an invalid " \
                        "state. Error: %s" % (devpath, ie), origin = self)
                continue
            except Exception, e:
                self._reporting.debug("There was an unexpected error: %s" % e, \
                        origin = self)
                continue

            self._reporting.info("Successfully restored changes to device " \
                    "%s." % devpath, \
                    origin = self)
        self._result = ReturnSuccess

    def clean(self):
        self._result = ReturnSuccess
