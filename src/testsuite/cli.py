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


import unittest, subprocess, os, os.path, exceptions

# List of messages that each plugin outputs when entering a task.
# for Plugincli1
enteringM1 = {
        "init"      :"INFO: Entering the init phase... (Plugincli1)",
        "prepare"   :"INFO: Entering the prepare phase... (Plugincli1)",
        "backup"    :"INFO: Entering the backup phase... (Plugincli1)",
        "restore"   :"INFO: Entering the restore phase... (Plugincli1)",
        "diagnose"  :"INFO: Entering the diagnose phase... (Plugincli1)",
        "fix"       :"INFO: Entering the fix phase... (Plugincli1)",
        "clean"     :"INFO: Entering the clean phase... (Plugincli1)"
        }

# List of messages that each plugin outputs when entering a task.
# for Plugincli2
enteringM2 = {
        "init"      :"INFO: Entering the init phase... (Plugincli2)",
        "prepare"   :"INFO: Entering the prepare phase... (Plugincli2)",
        "backup"    :"INFO: Entering the backup phase... (Plugincli2)",
        "restore"   :"INFO: Entering the restore phase... (Plugincli2)",
        "diagnose"  :"INFO: Entering the diagnose phase... (Plugincli2)",
        "fix"       :"INFO: Entering the fix phase... (Plugincli2)",
        "clean"     :"INFO: Entering the clean phase... (Plugincli2)"
        }

# List of messages that the Plugin System outputs.
psM = {
        "usingfix":"INFO: Using fix flow (Plugin System)"
        }

# List of messages that the Tasker outputs for Plugincli1
taskerM1 = {
        "flownoexist":"INFO: Plugin plugincli1 does not contain flow nonexistent (Task interpreter)"
        }

# List of messages that the Tasker outputs for Plugincli2
taskerM2 = {
        "flownoexist":"INFO: Plugin plugincli2 does not contain flow nonexistent (Task interpreter)"
        }

# FAK error message
fakerror = {
        "pluginnoexist":"FAK_ERROR: No plugin by the name of \"nonexistent\" was found."
        }


class FAKfirstaidkit__a(unittest.TestCase):
    def setUp(self):
        self.command = ["./firstaidkit", "-P", "testsuite/cli/", "-a"]
        (out, err) = subprocess.Popen(self.command, stdout=subprocess.PIPE, \
                stderr=subprocess.PIPE).communicate()
        self.output = out
        self.trueMes = [ "init", "prepare", "diagnose", "clean"]
        self.falseMes = [ "fix", "backup", "restore"]

    def testOutput(self):
        for elem in self.trueMes:
            self.assertTrue(enteringM1[elem] in self.output, \
                    "message: '%s' not preesnt in output" % \
                    enteringM1[elem])
            self.assertTrue(enteringM2[elem] in self.output, \
                    "message: '%s' not preesnt in output" % \
                    enteringM2[elem])

        for elem in self.falseMes:
            self.assertFalse(enteringM1[elem] in self.output, \
                    "message:'%s' is present in output" % \
                    enteringM1[elem])
            self.assertFalse(enteringM2[elem] in self.output, \
                    "message '%s' is presetn in output" % \
                    enteringM2[elem])

class FAKfirstaidkit__a_fix(unittest.TestCase):
    def setUp(self):
        self.command = ["./firstaidkit", "-P", "testsuite/cli/", "-a", "fix"]
        (out, err) = subprocess.Popen(self.command, stdout=subprocess.PIPE, \
                stderr=subprocess.PIPE).communicate()
        self.output = out
        self.mess = ["fix", "backup"]

    def testOutput(self):
        for elem in self.mess:
            self.assertTrue(enteringM1[elem] in self.output, \
                    "message: '%s' is not present in output" % \
                    enteringM1[elem])
            self.assertFalse(enteringM2[elem] in self.output, \
                    "message: '%s' is present in output" % \
                    enteringM2[elem])

        self.assertTrue(psM["usingfix"] in self.output, \
                "Plugin System '%s' message not in output" % \
                psM["usingfix"])


class FAKfirstaidkit__a_nonexistent(unittest.TestCase):
    def setUp(self):
        self.command = ["./firstaidkit", "-P", "testsuite/cli/", "-a", \
                    "nonexistent"]
        (out, err) = subprocess.Popen(self.command, stdout=subprocess.PIPE, \
                stderr=subprocess.PIPE).communicate()
        self.output = out

    def testOutput(self):
        self.assertTrue(taskerM1["flownoexist"] in self.output, \
                "Tasker '%s' message not present in output for plugincli1" % \
                taskerM1["flownoexist"])

        self.assertTrue(taskerM2["flownoexist"] in self.output, \
                "Tasker '%s' message not present in output for plugincli2" % \
                taskerM1["flownoexist"])

class FAKfirstaidkit__a__x_plugincli1(unittest.TestCase):
    def setUp(self):
        self.command = ["./firstaidkit", "-P", "testsuite/cli/", "-a", \
                    "-x", "plugincli1"]
        (out, err) = subprocess.Popen(self.command, stdout=subprocess.PIPE, \
                stderr=subprocess.PIPE).communicate()
        self.output = out

    def test1(self):
        for (key, val) in enteringM1.iteritems():
            self.assertFalse(val in self.output, \
                    "There was a message containing plugincli1 related "\
                    "messages")


class FAKfirstaidkit__f_nonexistent(unittest.TestCase):
    def setUp(self):
        self.command = ["./firstaidkit", "-P", "testsuite/cli/", "-f", \
                    "nonexistent"]
        (out, err) = subprocess.Popen(self.command, stdout=subprocess.PIPE, \
                stderr=subprocess.PIPE).communicate()
        self.output = out

    def test1(self):
        self.assertTrue(fakerror["pluginnoexist"] in self.output, \
                "FAK error 'nonexistent plugin' message not present in output")




class FAKfirstaidkit__f_plugincli1(unittest.TestCase):
    def setUp(self):
        self.command = ["./firstaidkit", "-P", "testsuite/cli/", "-f", \
                    "plugincli1"]
        (out, err) = subprocess.Popen(self.command, stdout=subprocess.PIPE, \
                stderr=subprocess.PIPE).communicate()
        self.output = out
        self.trueMes = ["init", "prepare", "diagnose", "clean"]
        self.falseMes = ["fix", "backup", "restore"]

    def testOutput(self):
        for elem in self.trueMes:
            self.assertTrue(enteringM1[elem] in self.output, \
                    "message: '%s' is not present in output" % \
                    enteringM1[elem])

        for elem in self.falseMes:
            self.assertFalse(enteringM1[elem] in self.output, \
                    "message: '%s' is present in output" % \
                    enteringM1[elem])

        # No plugincli2 messages should be present
        for elem in enteringM2:
            self.assertFalse(enteringM2[elem] in self.output, \
                    "message: '%s' is present in output" % \
                    enteringM2[elem])

class FAKfirstaidkit__f_plugincli1_fix(unittest.TestCase):
    def setUp(self):
        self.command = ["./firstaidkit", "-P", "testsuite/cli/", "-f", \
                    "plugincli1", "fix"]
        (out, err) = subprocess.Popen(self.command, stdout=subprocess.PIPE, \
                stderr=subprocess.PIPE).communicate()
        self.output = out
        self.trueMes = ["init", "prepare", "diagnose", "clean", "fix", "backup"]
        self.falseMes = ["restore"]

    def testOutput(self):
        for elem in self.trueMes:
            self.assertTrue(enteringM1[elem] in self.output, \
                    "message: '%s' is not present in output" % \
                    enteringM1[elem])

        for elem in self.falseMes:
            self.assertFalse(enteringM1[elem] in self.output, \
                    "message: '%s' is present in output" % \
                    enteringM1[elem])

        # No plugincli2 messages should be present
        for elem in enteringM2:
            self.assertFalse(enteringM2[elem] in self.output, \
                    "message: '%s' is present in output" % \
                    enteringM2[elem])

class FAKfirstaidkit__f_plugincli1_nonexistent(unittest.TestCase):
    def setUp(self):
        self.command = ["./firstaidkit", "-P", "testsuite/cli/", "-f", \
                    "plugincli1", "nonexistent"]
        (out, err) = subprocess.Popen(self.command, stdout=subprocess.PIPE, \
                stderr=subprocess.PIPE).communicate()
        self.output = out

    def testOutput(self):
        self.assertTrue(taskerM1["flownoexist"] in self.output)
