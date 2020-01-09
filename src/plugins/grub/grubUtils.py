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

import os, os.path, re, subprocess, tempfile, getopt
import minihal, parted
import pyfirstaidkit.utils as utils

# List of known or expected values for the system.
#
# Where the grub dir shoulc be with respect to the partition root.
locations = ["/boot/grub", "/grub"]

# The files that are expected to make grub work. nfiles -> needed files.
nfiles = ["stage1", "stage2"]

# Expected grub configuration file name.
conffile = "grub.conf"

# Expected mounts file
mounts = "/proc/mounts"

# Disks starting with these strings will be ignored when looking for system
# storage devices.
ignore_devs = ["sr"]

def get_all_devs():
    """Get all the storage devices that exists currently on the system.

    We only want the device name and the partitions for each device.
    We don't want the parted structures.
    Return - dictionary with device name and all device partitions.
    """

    # Must use an inner function as the test does not consider the device
    # number.  Olny device type.
    def is_dev_in_ignored(dev):
        for ignored in ignore_devs:
            if dev["device"].replace("/dev/","").startswith(ignored):
                return True
        return False

    retval = {}
    for device in minihal.get_devices_by_type("storage"):
        if device is None:
            continue

        elif is_dev_in_ignored(device):
            continue

        elif "storage.removable.media_available" in device.keys() and \
                device["storage.removable.media_available"] == False:
            # We ignore stuff that has no media inserted.
            continue

        else:
            try:
                # parted will provide us with all the partitions.
                partitions = []
                parteddev = parted.getDevice(device["device"])
                disk = parted.Disk(parteddev)
                for part in disk.partitions:
                    if part.type == parted.PARTITION_EXTENDED \
                            or part.type == parted.PARTITION_NORMAL \
                            or part.type == parted.PARTITION_LOGICAL:
                        partitions.append(
                                Dname("%s%s"%(device["device"],part.number)))
                # The key will be the device name and it will contain a list of
                # parts.  This is very unfortunate as the object would be better
                # sutied as a key.
                retval[Dname.asName(device["device"])] = partitions
            except:
                # If there is a problem with this dev... jus continue.
                continue

    return retval

def grub_dir_in_partition(part):
    """Search for the grub directory and all needed files in the partition

    It will search for the known locations and necessary files for in the
    specified partition.
    Return - list containing partitions with grub.
    """
    def do_unmount():
        part_unmount(part)
        if os.path.isdir(mountpoint):
            os.rmdir(mountpoint)


    # We search to see if the partition is mounted.  If its not we must
    # mount it in a temporary place to unmount it before we leave this
    # function.
    unmount=False
    mountpoint = is_part_mounted(part)
    if len(mountpoint) == 0:
        # This means that its not mounted. And we must unmount it at the
        # end.
        unmount=True

        # Select a safe temporary directory where to mount it.
        mountpoint = tempfile.mkdtemp(prefix=part.name())

        # If the mount fails it will raise an excpetion.  We must catch the
        # exception when this function is called.  Same goes for part_unmount.
        try:
            part_mount(part, mountpoint)
        except:
            # The partition was not mounted erase the directory if empty.
            # leave if the directoy is not empty
            os.rmdir(mountpoint)
            return False

    # Search for the grub directorie in the mounted partition.
    grubdir=""
    for dir in locations:
        if os.path.isdir(utils.join(mountpoint, dir)):
            grubdir=utils.join(mountpoint, dir)
            # We don't care if there is another directory in the same partition
            # It is very unlikely and not an intelligent thing to do anyway.
            break

    # At this point if we didn't find any of the locations, then grub is not
    # in this partition.
    if len(grubdir) == 0:
        if unmount:
            do_unmount()
        return False

    # Now we have to search for the files in the grub directory.  The list in
    # nfiles is the needed files.  So if one of the files is not found we
    # consider that there is not enough context to fix the issue in this part.
    # FIXME add some code that can replace the files that are missing.
    foundfiles = 0
    for file in nfiles:
        if os.path.isfile(utils.join(grubdir, file)):
            foundfiles = foundfiles + 1

    # If we don't have all the files we will not even consider this partition.
    if len(nfiles) > foundfiles:
        if unmount:
            do_unmount()
        return False

    # Search for the grub config file.
    if not os.path.isfile(utils.join(grubdir, conffile)):
        if unmount:
            do_unmount
        return False

    # FIXME need to implement the kernel and initrd image searching code.
    # for now we trust that the images are actually there.

    if unmount:
        do_unmount()

    return True

def is_part_mounted(part):
    """Search /proc/mounts for the presence of the partition.

    It searches for the "/dev/something" device.
    If its not mounted it returns an empty mountpoint (not mounted).
    If its mounted it returns the mount point.
    """
    for line in file(mounts).readlines():
        if re.search(part.path(), line) != None:
            # The mountpoint is in the second possition.
            return line.split(" ")[1]

    return ""

def part_mount(part, mountPoint, opts=None):
    """Mount the partition at mountpoint"""
    # Create the call
    call = ["mount"]
    if opts:
        call.append(opts)
    call.extend([part.path(), mountPoint])

    # Call mount
    proc = subprocess.Popen(call, stdout=subprocess.PIPE, \
            stderr=subprocess.PIPE)
    (out, err) = proc.communicate()
    retcode = proc.wait()
    if retcode != 0 or len(err) > 0:
        # The mount failed
        raise Exception("%s" % (part.path(), err))
    else:
        # This probably means that the mount succeded.
        return True

def part_unmount(part, opts=None):
    """Unmount the partition that is mounted at mountPoint

    part - It can actually be the part path or the mountpoint
    """

    # If its not a dev path its a mountpoint.
    if part.__class__.__name__ == "Dname":
        umountarg = part.path()
    else:
        umountarg = part

    # Create the call
    call = ["umount"]
    if opts:
        call.append(opts)
    call.append(umountarg)

    # Call umount
    proc = subprocess.Popen(call, stdout=subprocess.PIPE, \
            stderr=subprocess.PIPE)
    (out, err) = proc.communicate()
    retcode = proc.wait()
    if retcode != 0 or len(err) > 0:
        raise Exception("There was an error unmounting partition %s. " \
                "Error: %s." % (part.path(), err))
    else:
        return True


#
# There will be the possitility of installing the grub in all partitions
# that dont have a boot loader (This will hopefully be default behavior).
# For this purpose we must test to see if there are boot loaders in the
# device.
#
# The idea here is to have people scream about firstaidkit messing their
# other bootloaders up and creating new tests as needed.
#
# FIXME:If this function gets too big, might want to make another file.
def other_bootloader_present(dev):
    # Will allways say that no bootloader is present.
    def none_grub(dev):
        return False

    # Check for presence of windows bootloader.  This is taken out of
    # http://en.wikipedia.org/wiki/Master_boot_record, if anyone can
    # point me to a better source, please do.  Moreover, if anyone can
    # come up with a better way of doing this please send patch.
    windowsStrings = ["Invalid partition table", \
                      "Error loading operating system" \
                      "Missing operating system"]
    def windows_boot_loader(dev):

        # read the first 512 bytes of device.
        fd = os.open(dev.path(), os.O_RDONLY)
        first512b = os.read(fd, 512)
        os.close(fd)

        # Search for the strings that will give the windows partition away.
        # We assert that its windows when all the strings are found.
        foundstrings = 0
        for string in windowsStrings:
            if re.search(string, first512b) != None:
                foundstrings = foundstrings + 1

        if foundstrings == len(windowsStrings):
            return True

        return False

    # We will have the list of all the tests in the tests variable.
    tests = [none_grub]

    for test in tests:
        if test(dev):
            return True

    return False

# The Strings contained in the grub stage one:
stage1strings = ["GRUB", "Geom", "Hard", "Disk", "Read", "Error"]

def grub_bin_in_dev(dev):
    """Will look in the first 446 bytes of the device for traces of grub.

    Will look for the strings that come with the grub stage1 image.  The
    strings are: "GRUB", "Geom", "Hard", "Disk", "Read" and "Error".  These
    strings must be compared considering the letter case.
    dev - Dname object representing the storage device.
    """
    if (os.path.exists(dev.path())):

        # Read the first 446 bytes of the dev.
        fd = os.open(dev.path(), os.O_RDONLY)
        first446b = os.read(fd, 446)
        os.close(fd)

        # Search for all the strings
        foundstrings = 0
        for string in stage1strings:
            if re.search(string, first446b) != None:
                foundstrings = foundstrings + 1

        # Only if all the strings are present we give the goahead.
        if foundstrings == len(stage1strings):
            return True

    return False


def grub_bin_in_part(part):
    """Will look in the first 446 bytes of the partition for traces of grub.

    Same conditions apply as in grub_bin_in_dev.
    """
    return grub_bin_in_dev(part)

# Input string for the grub batch mode.
# FIXME: Do we need lba, stage2 specification, prefix?
batch_grub_install = """
root (%s)
setup (%s)
quit
"""
def install_grub(root, setup):
    """Install stage1 grub image in the specified place.

    root -  the root where the dir is.  This can be a divice or partition.
            It must be a Dname
    setup - the dev where to install image. This can be device or partition.
            It must be a Dname

    return - whatever the grub console puts on stdout.
    """

    # Construct the root string.
    grubroot = root.grubName()
    grubsetup = setup.grubName()

    # Run the command that installs the grub.
    # FIXME: We are not taking into account the device map.
    command = ["grub", "--batch"]
    proc = subprocess.Popen(command, stdout = subprocess.PIPE,
            stdin = subprocess.PIPE, stderr = subprocess.PIPE)
    (out, err) =  proc.communicate(batch_grub_install%(grubroot, grubsetup))

    m = re.search("Error.*\\n", "%s%s"%(out,err))
    if m != None:
        # raise an exception when grub shell returned an error.
        raise Exception("There was an error while installing grub. Error %s " \
                % m.group(0))

    return out

def find_grub_root(grub_dir_parts):
    return grub_dir_parts[0]

# Function to parse the user options.
def get_grub_opts(args):
    """ Function to parse user options.

    --install-all : This option will tell grub plugin that it must not ignore
                    any devices that have other bootloaders.  In other word
                    its telling the plugin to install in all possible places.
                    In case --installto-devs is also defined allong side this
                    options, we will choose the list from installto-devs

    --install-auto : This will try to avoid overwriting other bootloaders.

    --installto-devs=dev1,dev2... : This tells the grub plugin the specific
                                    devices that should be considered for
                                    installation.  All other devices will be
                                    ignored.  If install-all is selected with
                                    this option, we will prefer the list
                                    described in installto-devs.

    --installto-parts=part1,part2... : The same as install to devs but give
                                       a list of partitions.

    --recover-devs=dev1,dev2 : Same as --installto-devs, just more intuitive
                               for the user that does not know how grub works.

    --recover-parts=part1,part2 : Same as recover-devs but specifies the
                                  partitions to be recovered.

    We will return a object with all de relative information.
    """

    # Create the object with the argument decision.
    class grub_args:
        install_all = False
        install_auto = False
        installto_devs = []
        installto_parts = []
    retval = grub_args()

    # Parse the args string
    optsstr = ""
    longopts = ["install-all", "install-auto", \
                "installto-devs=", "recover-devs=", \
                "installto-parts=", "recover-parts="]
    try:
        (opts, vals) = getopt.getopt( args.split(), optsstr, longopts )
    except:
        # FIXME: put some sort of exception here so the use can know when
        # he passed the wrong params.
        # FIXME: there can also be the case the it fails because the split
        # is done to somehting that is not a string.
        pass

    for (opt, val) in opts:

        # install all will be considered if no devs or parts have been parsed.
        if opt == "--install-all" and \
                (len(retval.installto_devs) + len(retval.installto_parts) == 0):
            retval.install_all = True
            retval.install_auto = False

        # install auto is valid only when all other optiosn are not passed.
        if opt == "--install-auto" and not retval.install_all and \
                (len(retval.installto_devs) + len(retval.installto_parts) == 0):
                retval.install_auto = True

        if opt in ( "--installto-devs", "--recover-devs" ):
            retval.installto_devs = val.split(',')
            retval.install_all = False
            retval.install_auto = False

        if opt in ( "--installto-parts", "--recover-parts" ):
            retval.installto_parts = val.split(',')
            retval.install_all = False
            retval.install_auto = False



    return retval




# I really don't like the fact that you can have a variable that represents
# a device or partition and not know, until runtime, with total certainty,
# if its "/dev/something" or just "something".

# The constant to transform a device leter to a grub hd number. ciconst
# (char int constant)
ciconst = ord('a')
class Dname:
    """Class to represent device names.

    It will only represent device and partitiosn.
    """
    # FIXME: extend this class to raid.
    def __init__(self, name):
        if name.__class__.__name__ == "Dname":
            self.dname = name.dname
        elif name.startswith("/dev/"):
            self.dname = name[5:]
        else:
            self.dname = name

    @classmethod
    def asPath(self, dev):
        """return the device in the "/dev/somthing" form."""
        if dev.__class__.__name__ == "Dname":
            return dev.path()
        else:
            temp = Dname(dev)
            return temp.path()

    @classmethod
    def asName(self, dev):
        """return the device in the "somthing" form"""
        if dev.__class__.__name__ == "Dname":
            return dev.name()
        else:
            temp = Dname(dev)
            return temp.name()

    @classmethod
    def asGrubName(self, dev, parenthesis = False):
        """return something that grub understands."""
        if dev.__class__.__name__ == "Dname":
            return dev.grubName(parenthesis)
        else:
            temp = Dname(dev)
            return temp.grubName(parenthesis)

    def path(self):
        return utils.join("/dev/", self.dname)

    def name(self):
        return self.dname

    def grubName(self, parenthesis = False):
        """Change the kernel device name to something that grub understands

        It returns a string of the form hd[device],[partition]
        """

        # First we search for the number that ends the device string.
        m = re.search("[0-9]+$", self.dname)
        if m == None:
            partnum = None
            devnum = ord(self.dname[len(self.dname)-1]) - ciconst
        else:
            # The grub partition number scheme is a little different.  Its safe
            # to assume that its one less than the usual scheme.
            partnum = int(m.group(0))
            temp = self.dname.strip(str(partnum))

            # Follow grub scheme
            partnum = partnum - 1

            # We now get the letter that is before the number
            devnum = ord(temp[len(temp)-1]) - ciconst

        # Must check to see if the values are in range.
        if (partnum != None and partnum < 0) or (devnum < 0):
            raise Exception("The conversion from kernel device scheme to " \
                    "grub scheme failed.")

        # Decide weather to return with or without parenthesis.
        if parenthesis:
            openpar = "("
            closepar = ")"
        else:
            openpar = ""
            closepar = ""

        # Create the grub device string.
        if partnum == None:
            return "%shd%s%s"%(openpar, devnum, closepar)
        else:
            return "%shd%s,%s%s"%(openpar, devnum, partnum, closepar)

