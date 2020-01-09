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

from pyfirstaidkit.configuration import Config
from pyfirstaidkit.plugins import Plugin,Flow
from pyfirstaidkit.reporting import PLUGIN
from pyfirstaidkit.returns import *
from pyfirstaidkit.issue import SimpleIssue
import os.path
import openscap_api as openscap
import time

class OpenSCAPPlugin(Plugin):
    """Performs security audit according to the SCAP policy"""
    name = "OpenSCAP audit"
    version = "0.1.0"
    author = "Martin Sivak <msivak@redhat.com>"

    flows = Flow.init()
    flows["oscap_scan"] = Flow({
        Plugin.initial: {Return: "prepare"},
        "prepare": {ReturnSuccess: "policy", ReturnFailure: "clean"},
        "policy": {ReturnSuccess: "rules", ReturnFailure: "clean",
                   ReturnAbort: "clean"},
        "rules": {ReturnSuccess: "tailoring", ReturnFailure: "clean",
                  ReturnBack: "policy", ReturnAbort: "clean"},
        "tailoring": {ReturnSuccess: "diagnose", ReturnFailure: "clean",
                      ReturnBack: "rules", ReturnAbort: "clean"},
        "diagnose": {ReturnSuccess: "results", ReturnFailure: "clean"},
        "results": {ReturnSuccess: "clean", ReturnFailure: "clean"},
        "clean": {ReturnSuccess: Plugin.final}
        }, description = "Performs a security and configuration audit of running system")
    flows["oscap_scan"].title = "Security Audit"

    def __init__(self, *args, **kwargs):
        Plugin.__init__(self, *args, **kwargs)
        self._oval = "/usr/share/openscap/oval.xml"
        self._xccdf = "/usr/share/openscap/scap-xccdf.xml"
        self._issues = {}
    
    def prepare(self):
        try:
            self._objs = openscap.xccdf.init(self._xccdf)
        except ImportError, e:
            self._reporting.error(str(e), origin = self, level = PLUGIN)
            self._result=ReturnFailure
            return
        
        self._xccdf_policy_model = self._objs["policy_model"]
        self._policy = None
        
        self._xccdf_policy_model.register_output_callback(self.oscap_callback, self)
        self._xccdf_policy_model.register_start_callback(self.oscap_callback_start, self)
        
        self._reporting.info("OpenSCAP initialized", origin = self, level = PLUGIN)
        self._result=ReturnSuccess

    def policy(self):
        # Select the only available policy
        if len(self._xccdf_policy_model.policies)==1:
            self._result=ReturnSuccess
            self._policy = self._xccdf_policy_model.policies[0]
            return

        if not Config.operation.interactive == "True":
            self._result=ReturnSuccess
            self._policy = self._xccdf_policy_model.policies[-1]
            return
        
        all_policies = map(lambda p: (
            p.id,
            p.profile and len(p.profile.title) and p.profile.title[0].text or "Default profile",
            p.id == None and True or False,
            p.profile and p.profile.description or "",
            "", ""
            ), self._xccdf_policy_model.policies)

        s = self._reporting.config_question_wait("Choose OpenScap profile",
                                                 "Select desired profile and press OK",
                                                 all_policies,
                                                 options = {"mode": 3, "back": False},
                                                 origin = self,
                                                 level = PLUGIN)
        if s in (ReturnBack, ReturnAbort):
            self._result = s
            return
        
        for idx, (id, val) in enumerate(s):
            if val:
                self._policy = self._xccdf_policy_model.policies[idx]
                self._reporting.info("OpenSCAP policy %s selected" % (id,), origin = self, level = PLUGIN)
            
        if self._policy is None:
            self._result=ReturnFailure
            self._reporting.error("OpenSCAP policy failed to initialize", origin = self, level = PLUGIN)
        else:
            self._reporting.info("OpenSCAP policy initialized", origin = self, level = PLUGIN)
            self._result=ReturnSuccess

    def rules(self):
        if not Config.operation.interactive == "True":
            self._result=ReturnSuccess
            return

        all_rules = self._policy.get_selects()
        if len(all_rules) == 0:
            self._result=ReturnSuccess
            return
        
        preprocess_rules = lambda x: (x.item,
                                      self._policy.model.benchmark.get_item(x.item).title[0].text,
                                      x.selected and True,
                                      self._policy.model.benchmark.get_item(x.item).description[0].text,
                                      "",
                                      "Use checkbox disable or enable rule"
                                      )
        all_rules = map(preprocess_rules, all_rules)
        s = self._reporting.config_question_wait("Setup OpenScap rules",
                                                 "Enable or disable rules and press OK",
                                                 all_rules,
                                                 options = {"mode": 1},
                                                 origin = self,
                                                 level = PLUGIN)
        if s in (ReturnBack, ReturnAbort):
            self._result = s
            return
        
        enabled_rules = []
        for r in s:
            if r[1]:
                enabled_rules.append(r[0])

        self._policy.set_rules(enabled_rules)
        self._reporting.info("Enabled rules: %s" % repr(enabled_rules), origin = self,
                             level = PLUGIN)
        
        self._result=ReturnSuccess

    def tailoring(self):
        if not Config.operation.interactive == "True":
            self._result=ReturnSuccess
            return

        tailor_items = self._policy.get_tailor_items()
        if len(tailor_items) == 0:
            self._result=ReturnSuccess
            return
        
        preproces_tailor_items = lambda i: (i["id"],
                                            i["titles"][i["lang"]] or "",
                                            i["selected"][1] or "",
                                            i["descs"][i["lang"]] or "",
                                            i["match"] or ".*",
                                            "Error setting the value, read the following description and try again:\n\n"+i["descs"][i["lang"]],
                                            set(i["options"].values())
                                            )
        tailor_items = map(preproces_tailor_items, tailor_items)

        s = self._reporting.config_question_wait("Setup OpenScap policy",
                                                 "Set preferred values and press OK",
                                                 tailor_items,
                                                 options = {"mode": 2},
                                                 origin = self,
                                                 level = PLUGIN)

        if s in (ReturnBack, ReturnAbort):
            self._result = s
            return
        
        preprocess_s = lambda v: {"id": v[0], "value": v[1]}
        s = map(preprocess_s, s)
        
        self._policy.set_tailor_items(s)
        self._reporting.info("Tailoring Done", origin = self, level = PLUGIN)  
        self._result=ReturnSuccess
            
    def oscap_callback(self, Msg, Plugin):
        if Msg.user2num == openscap.OSCAP.XCCDF_RESULT_NOT_SELECTED:
            if Plugin.continuing():
                return 0
            else:
                return 1
            
        try:       
            Id = Msg.user1str
            result = Msg.user2num
            setattr(self._info, Id, unicode(result))
            Issue = Plugin._issues.get(Id, None)
            Issue.set(skipped = (result in
                                 (openscap.OSCAP.XCCDF_RESULT_NOT_CHECKED,
                                  openscap.OSCAP.XCCDF_RESULT_NOT_SELECTED,
                                  openscap.OSCAP.XCCDF_RESULT_NOT_APPLICABLE,
                                  openscap.OSCAP.XCCDF_RESULT_UNKNOWN)),
                      checked = (result in
                              (openscap.OSCAP.XCCDF_RESULT_FAIL,
                               openscap.OSCAP.XCCDF_RESULT_PASS)),
                      error = (result in
                              (openscap.OSCAP.XCCDF_RESULT_ERROR,)),
                      happened = (result == openscap.OSCAP.XCCDF_RESULT_FAIL),
                      fixed = False,
                      reporting  = Plugin._reporting,
                      origin = Plugin,
                      level = PLUGIN)
        except Exception, e:
            print e

        if Plugin.continuing():
            return 0
        else:
            return 1        
        
        
    def oscap_callback_start(self, Msg, Plugin):
        if Msg.user2num == openscap.OSCAP.XCCDF_RESULT_NOT_SELECTED:
            if Plugin.continuing():
                return 0
            else:
                return 1
           
        
        try:
            Id = Msg.user1str
            setattr(self._info, Id, unicode(-1))
            Issue = Plugin._issues.get(Id, None)
            if Issue is None:
                title = Msg.user3str
                description = Msg.string
                Issue = SimpleIssue(Id, title)
                Issue.set(reporting  = Plugin._reporting, origin = Plugin, level = PLUGIN)
                Plugin._issues[Id] = Issue
               
        except Exception, e:
            print e

        if Plugin.continuing():
            return 0
        else:
            return 1


    def diagnose(self):
        for x in self._policy.get_selected_rules():
            self._reporting.info("Selecting rule "+x.item, origin = self, level = PLUGIN)

        self._reporting.info("Starting OpenSCAP evaluation", origin = self, level = PLUGIN)
        self._oscap_result = self._policy.evaluate()
        self._result=ReturnSuccess

    def results(self):
        print self._objs
        files = self._policy.export(self._oscap_result, "OpenSCAP results",
                                    "/tmp/oscap_results.xml", "/tmp/oscap_res_",
                                    self._objs["xccdf_path"], self._objs["sessions"])
        for f in files:
            self._info.attach(f, os.path.basename(f))
        self._result=ReturnSuccess
        
    def clean(self):
        #openscap.xccdf.destroy(self._objs)
        self._reporting.info("OpenSCAP deinitialized", origin = self, level = PLUGIN)
        self._result=ReturnSuccess


def get_plugin():
    return OpenSCAPPlugin
