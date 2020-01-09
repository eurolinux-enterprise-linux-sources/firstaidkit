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


import unittest, imp, py_compile, os, os.path
from pyfirstaidkit import Config
from pyfirstaidkit import initLogger
from pyfirstaidkit.plugins import PluginSystem
from pyfirstaidkit.reporting import Reports
from pyfirstaidkit.dependency import Dependencies

class Initialization(unittest.TestCase):
    def setUp(self):
        self.contentdir = "testsuite/initialization"
        self.confPath = self.contentdir+"/initialization.conf"
        Config.read(self.confPath)
        initLogger(Config)
        self.pluginSystem = PluginSystem(reporting=Reports(),
                dependencies=Dependencies())
        self.plugin = self.pluginSystem.getplugin("pluginInfo")
        py_compile.compile("%s/pycFile" % self.contentdir,
                cfile="%s/pycFile.pyc" % self.contentdir)

    def tearDown(self):
        if(os.path.isfile(Config.log.filename)):
            os.remove(Config.log.filename)

class Imports(Initialization):
    """Tests the capability of importing 3 typs of files."""

    def testImportsPy(self):
        self.assert_('pyFile' in self.pluginSystem.list(),
                "Firstaidkit failed to import a 'py' file.")

    def testImportsPyc(self):
        self.assert_('pycFile' in self.pluginSystem.list(),
                "Firstaidkit failed to import a 'pyc' file.")

    def testImportsDir(self):
        self.assert_('directory' in self.pluginSystem.list(),
                "Firstaidkit failed to import from a directory.")

class Info(Initialization):
    """Test the infomration from the plugins."""
    def testInfoName(self):
        self.assertEqual(self.plugin.name, "TestInfoPlugin")

    def testInfoAuthor(self):
        self.assertEqual(self.plugin.author, "John Galt")

    def testInfoVersion(self):
        self.assertEqual(self.plugin.version, "3.4.5")

    def testInfoFlowName(self):
        self.assert_('newflow' in self.plugin.getFlows(),
                "Firstaidkit failed to show access the flow name")

    def testInfoFlowDescription(self):
        self.assert_('This is the newflow' == \
                self.plugin.getFlow("newflow").description,
                "Firstaidkit failed to show access the flow name")

