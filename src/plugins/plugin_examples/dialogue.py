# coding=utf-8
# First Aid Kit - diagnostic and repair tool for Linux
# Copyright (C) 2009 Red Hat, Inc.
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
#
# Red Hat author: Miloslav Trmač <mitr@redhat.com>

from pyfirstaidkit.plugins import Plugin,Flow
from pyfirstaidkit.reporting import PLUGIN
from pyfirstaidkit.returns import *
from pyfirstaidkit.issue import SimpleIssue
from pyfirstaidkit.configuration import Config

class DialoguePlugin(Plugin):
    """This plugin demonstrates asking the user for information."""
    name = "DialoguePlugin"
    version = "0.0.2"
    author = "Miloslav Trmač & Martin Sivák"

    def __init__(self, *args, **kwargs):
        Plugin.__init__(self, *args, **kwargs)
        self._issue = SimpleIssue(self.name, self.description)

    @classmethod
    def getDeps(cls):
        return set(["interactive"]).union(Plugin.getDeps())

    def prepare(self):
        self._issue.set(reporting = self._reporting, origin = self,
                        level = PLUGIN)
        self._result=ReturnSuccess
            
    def backup(self):
        self._result=ReturnSuccess

    def restore(self):
        self._result=ReturnSuccess

    def diagnose(self):
        self._result=ReturnSuccess
        self._reporting.info("DialoguePlugin in diagnose task", origin = self,
                             level = PLUGIN)
        tea = self._reporting.choice_question_wait \
            ("Would you care for some tea?", ((True, "Yes"), (False, "No")),
             origin = self, level = PLUGIN)
        if tea:
            self._reporting.info("Here's your tea", origin = self,
                                 level = PLUGIN)
        else:
            self._reporting.info("No tea for you!", origin = self,
                                 level = PLUGIN)
        s = self._reporting.text_question_wait("Enter your name: ",
                                               origin = self, level = PLUGIN)
        self._reporting.info("Name: %s" % repr(s), origin = self,
                             level = PLUGIN)
        s = self._reporting.password_question_wait("Old fake password: ",
                                                   origin = self,
                                                   level = PLUGIN)
        self._reporting.info("Old password: %s" % repr(s), origin = self,
                             level = PLUGIN)
        s = self._reporting.password_question_wait("New fake password: ",
                                                   confirm = True,
                                                   origin = self,
                                                   level = PLUGIN)
        self._reporting.info("New password: %s" % repr(s), origin = self,
                             level = PLUGIN)
        s = self._reporting.filename_question_wait("File name: ", origin = self,
                                                   level = PLUGIN)
        self._reporting.info("File name: %s" % repr(s), origin = self,
                             level = PLUGIN)

        config_options = [
            ("id:1", "PL", "5", "Password length", "[1-9][0-9]*", "The length must be a valid number bigger than 0."),
            ("id:2", "PS", "C", "Password strength", "[A-F]", "Use strength indicator A, B, C, D, E or F"),
            ("id:3", "PL", "aA0.", "Password chars", ".*", "Any allowed characters.."),
            ]

        s = self._reporting.config_question_wait("Setup choices",
                                                 "Set preferred values",
                                                 config_options, origin = self,
                                                 level = PLUGIN)
        self._reporting.info("Options: %s" % repr(s), origin = self,
                             level = PLUGIN)

        self._issue.set(checked = True, happened = False,
                        reporting = self._reporting, origin = self,
                        level = PLUGIN)

    def fix(self):
        self._result=ReturnSuccess

    def clean(self):
        self._result=ReturnSuccess

def get_plugin():
    return DialoguePlugin
