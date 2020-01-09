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

import os
import shutil

from pyfirstaidkit.plugins import Plugin,Flow
from pyfirstaidkit.reporting import PLUGIN
from pyfirstaidkit.returns import *
from pyfirstaidkit.issue import SimpleIssue

class FreeSpacePlugin(Plugin):
    """Plugin to detect insufficient free space in /var directory."""
    name = "Free Space"
    version = "0.0.1"
    author = "Tomas Mlcoch"
    description = "Detects insufficient free space in /var directory."

    directory = '/var'
    del_dirs = ['/var/tmp',] # All content of this files will be
                             # removed (deleted) in "fix" step.

    @classmethod
    def getDeps(cls):
        return set(["root", "filesystem"])
    
    def __init__(self, *args, **kwargs):
        Plugin.__init__(self, *args, **kwargs)
        self._issue = SimpleIssue(self.name, self.description)

    def _reporter(self, msg):
        self._reporting.info(msg, origin=self, level=PLUGIN)

    def prepare(self):
        self._issue.set(reporting=self._reporting, origin=self, level=PLUGIN)
        self._result=ReturnSuccess

    def diagnose(self):
    
        # statvfs stucture:
        # -----------------
        # f_bsize   File system block size.
        # f_frsize  Fundamental file system block size (fragment size).
        # f_blocks  Total number of blocks on the file system, in units of f_frsize.
        # f_bfree   Total number of free blocks.
        # f_bavail  Total number of free blocks available to non-privileged processes.
        # f_files   Total number of file nodes (inodes) on the file system.
        # f_ffree   Total number of free file nodes (inodes).
        # f_favail  Total number of free file nodes (inodes) available to non-privileged processes.
        # f_flag    File system ID number.
        # f_namemax Maximum length of a file name (path element).
        
        # stat structure:
        # ---------------
        # st_dev        device
        # st_ino        inode
        # st_mode       protection
        # st_nlink      number of hard links
        # st_uid        user ID of owner
        # st_gid        group ID of owner
        # st_rdev       device type (if inode device)
        # st_size       total size, in bytes
        # st_blksize    blocksize for filesystem I/O
        # st_blocks     number of blocks allocated
        # st_atime      time of last access
        # st_mtime      time of last modification
        # st_ctime      time of last change

        # Get freespace
        stats = os.statvfs(self.directory)
        freespace = stats.f_bavail * stats.f_frsize / 1048576  # Freespace in Mb
        
        # Get freeable space
        self.freeable = 0
        for dir in self.del_dirs:
            stats_fa = os.statvfs(dir)
            for root, dirs, files in os.walk(dir):
                for d in dirs:
                    self.freeable += os.stat(os.path.join(root, d)).st_size
                for f in files:
                    self.freeable += os.stat(os.path.join(root, f)).st_size
        self.freeable /= 1024

        # Analyse results
        if freespace < 1:
            lhappened = True
            self._reporter("Free space seems to be insufficient.")
            self._reporter("Freeable space: %s Kb" % self.freeable)
            self._result=ReturnFailure
        else:
            lhappened = False
            self._reporter("Free space seems to be sufficient.")
            self._result=ReturnSuccess
        
        self._issue.set(checked=True, happened=lhappened,
            reporting=self._reporting, origin=self, level=PLUGIN)

    def backup(self):
        self._result=ReturnSuccess

    def restore(self):
        self._result=ReturnSuccess

    def fix(self):
        try:
            for dir in self.del_dirs:
                self._reporter("Deleting content of: %s" % dir)
                for root, dirs, files in os.walk(dir):
                    for d in dirs:
                        shutil.rmtree(os.path.join(root, d))
                    for f in files:
                        os.unlink(os.path.join(root, f))
        except (Exception) as e:
            self._reporter("Exception: %s" % e)
            self._result=ReturnFailure
        else:
            self._result=ReturnSuccess
            self._reporter("Fix successfully complete! (Freed space: %s Kb)" \
                                % self.freeable)        
            
        self._issue.set(fixed=(self._result == ReturnSuccess), 
                reporting=self._reporting, origin=self, level=PLUGIN)

    def clean(self):
        self._result=ReturnSuccess

def get_plugin():
    return FreeSpacePlugin

