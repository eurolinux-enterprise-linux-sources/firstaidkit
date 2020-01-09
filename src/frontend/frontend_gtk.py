# File name: main.py
# Date:      2008/04/21
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

import gtk
import gtk.glade
import gobject #we need gobject.idle_add
import copy
import logging
from pyfirstaidkit import reporting
from pyfirstaidkit.returns import *
from pyfirstaidkit.configuration import resetInfo, FAKConfig
import pprint
import os.path
import thread
import hashlib
import re

def _o(func, *args, **kwargs):
    """Always return False -> remove from the idle queue after first
    execution"""
    
    func(*args, **kwargs)
    return False


class CallbacksMainWindow(object):
    def __init__(self, dialog, cfg, info, tasker, glade, data):
        self._dialog = dialog
        self._tasker = tasker
        self._glade = glade
        self._cfg = cfg
        self._info = info
        self._data = data
        self._running_lock = thread.allocate_lock()

    def execute(self):
        if not self._running_lock.acquire(0):
            return

        def _o2(pages, pagesstate, enablebuttons, disablebuttons):
            """Always return False -> remove from the idle queue after first
            execution"""
            
            for i in range(pages.get_n_pages())[:-1]:
                pages.get_nth_page(i).set_sensitive(pagesstate)
            map(lambda b: b.set_sensitive(False), disablebuttons)
            map(lambda b: b.set_sensitive(True), enablebuttons)
            
            return False

        def worker(pages, runningbuttons, stoppedbuttons):
            gobject.idle_add(_o2, pages, False, runningbuttons, stoppedbuttons)
            self._cfg.lock()
            self._tasker.run()
            self._cfg.unlock()
            gobject.idle_add(_o2, pages, True, stoppedbuttons, runningbuttons)
            self._running_lock.release()

        self._data.pages.set_current_page(-1)
        for i in range(self._data.pages.get_n_pages())[:-1]:
            self._data.pages.get_nth_page(i).set_sensitive(False)
        self.on_b_ResetResults_activate(None)

        stopbutton = self._glade.get_widget("b_StopResults")
        saveresmenu = self._glade.get_widget("save_results_menu")
        saveresbutton = self._glade.get_widget("save_results_button")
        resetresbutton = self._glade.get_widget("b_ResetResults")
        thread.start_new_thread(worker, (self._data.pages, [stopbutton], [resetresbutton, saveresmenu, saveresbutton]))

    #menu callbacks
    def on_mainmenu_open_activate(self, widget, *args):
        print("on_mainmenu_open_activate")
        d = gtk.FileChooserDialog(title="Load the configuration file",
                parent=self._dialog, action=gtk.FILE_CHOOSER_ACTION_OPEN,
                buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT, gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        fil = gtk.FileFilter()
        fil.set_name("FirstAidKit ini files (*.ini)")
        fil.add_pattern("*.ini")
        d.add_filter(fil)

        ret = d.run()

        if ret==gtk.RESPONSE_ACCEPT:
            try:
                filename = d.get_filename()
                self._cfg.read(filename)
                self._data.refresh()
            except IOError, e:
                print e

        d.destroy()
        return True

    def on_mainmenu_save_activate(self, widget, *args):
        print("on_mainmenu_save_activate")
        d = gtk.FileChooserDialog(title="Save the configuration file",
                parent=self._dialog, action=gtk.FILE_CHOOSER_ACTION_SAVE,
                buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT, gtk.STOCK_OK,
                    gtk.RESPONSE_ACCEPT))
        d.set_filename("firstaidkit.ini")
        fil = gtk.FileFilter()
        fil.add_pattern("*.ini")
        fil.set_name("FirstAidKit ini files (*.ini)")
        d.add_filter(fil)

        ret=d.run()

        if ret==gtk.RESPONSE_ACCEPT:
            try:
                filename = d.get_filename()
                fd = open(filename, "w")
                self._cfg.write(fd)
            except IOError, e:
                print e

        d.destroy()
        return True

    def on_mainmenu_save_results_activate(self, widget, *args):
        d = gtk.FileChooserDialog(title="Save the results file",
                parent=self._dialog, action=gtk.FILE_CHOOSER_ACTION_SAVE,
                buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT, gtk.STOCK_OK,
                    gtk.RESPONSE_ACCEPT))
        d.set_filename("results.zip")
        fil = gtk.FileFilter()
        fil.add_pattern("*.zip")
        fil.set_name("FirstAidKit result archives (*.zip)")
        d.add_filter(fil)
        ret=d.run()

        if ret==gtk.RESPONSE_ACCEPT:
            try:
                filename = d.get_filename()
                self._info.dump(filename)
            except IOError, e:
                print e

        d.destroy()
        return True

    def on_quit_activate(self, widget, *args):
        print("on_quit_activate")
        #XXX destroy right now, but warn, in final code we have to wait until
        #plugin finishes
        if True:
            print("!!! You should wait until the running plugin finishes!!")
            self._dialog.destroy()
        return True

    def on_destroy(self, widget, *args):
        print("on_destroy")
        self._tasker.end()
        del self._tasker
        del self._cfg
        del self._data.result_list_iter
        gtk.main_quit()

    def on_mainmenu_about_activate(self, widget, *args):
        print("on_mainmenu_about_activate")
        AboutDialog(self._cfg,
                dir = os.path.dirname(self._glade.relative_file(".")))
        return True

    def on_mainmenu_expert_activate(self, widget, *args):
        self._glade.get_widget("expert_page").show()
        self._data.pages.set_current_page(1)
        return True
        
    #advanced mode callbacks
    def populate_advanced(self, cfg):
        # get flags
        flags = set(self._cfg.operation._list("flags"))
        
        #set the auto-flow
        cfg.operation.mode = "auto-flow"

        idx = self._data.flow_list.get_active_iter()
        if idx is None:
            return True
        cfg.operation.flow = self._data.flow_list_store.get_value(idx,0)

        #check verbose
        if self._glade.get_widget("check_Advanced_Verbose").get_active():
            cfg.operation.verbose = "True"
        else:
            cfg.operation.verbose = "False"

        #check experimental
        if self._glade.get_widget("check_Advanced_Experimental").get_active():
            flags.add("experimental")
        else:
            try:
                flags.remove("experimental")
            except KeyError, e:
                pass

        #check interactive
        if self._glade.get_widget("check_Advanced_Interactive").get_active():
            cfg.operation.interactive = "True"
        else:
            cfg.operation.interactive = "False"

        #check dependency
        if self._glade.get_widget("check_Advanced_NoDependency").get_active():
            cfg.operation.dependencies = "False"
        else:
            cfg.operation.dependencies = "True"

        cfg.operation.flags = " ".join(
            map(lambda x: x.encode("string-escape"), flags))

        #reset params
        if cfg.has_section("plugin-args"):
            cfg.remove_section("plugin-args")
        cfg.add_section("plugin-args")

        return cfg


    def on_b_StartAdvanced_activate(self, widget, *args):
        print("on_b_StartAdvanced_activate")

        self.populate_advanced(self._cfg)
        self.execute()
        return True

    #expert mode callbacks
    def on_b_FlagsExpert_activate(self, widget, *args):
        print("on_b_FlagsExpert_activate")
        FlagList(self._cfg, self._tasker.flags(),
                dir = os.path.dirname(self._glade.relative_file(".")))
        return True

    def on_b_InfoExpert_activate(self, widget, *args):
        print("on_b_InfoExpert_activate")

        path,focus = self._data.plugin_list.get_cursor()
        if path is None:
            return True

        iter = self._data.plugin_list_store.get_iter(path)
        pluginname = self._data.plugin_list_store.get_value(iter, 4)
        print("Selected: %s"% pluginname)

        PluginInfo(self._tasker.pluginsystem().getplugin(pluginname),
                dir = os.path.dirname(self._glade.relative_file(".")))

        return True

    def on_b_StartExpert_activate(self, widget, *args):
        print("on_b_StartExpert_activate")

        #check verbose
        if self._glade.get_widget("check_Expert_Verbose").get_active():
            self._cfg.operation.verbose = "True"
        else:
            self._cfg.operation.verbose = "False"

        #check interactive
        if self._glade.get_widget("check_Expert_Interactive").get_active():
            self._cfg.operation.interactive = "True"
        else:
            self._cfg.operation.interactive = "False"

        #check dependency
        if self._glade.get_widget("check_Expert_NoDependency").get_active():
            self._cfg.operation.dependencies = "False"
        else:
            self._cfg.operation.dependencies = "True"

        #get the plugin & flow list
        plugins = []
        flows = []

        #reset params
        if self._cfg.has_section("plugin-args"):
            self._cfg.remove_section("plugin-args")
        self._cfg.add_section("plugin-args")

        for pname,iter in self._data.plugin_iter.iteritems():
            #get/set plugin params
            param = self._data.plugin_list_store.get_value(iter, 3)
            if param.strip()!="":
                val = "%s %s" % (pname, param)
                self._cfg.set("plugin-args", hashlib.sha1(val).hexdigest(), val)

            #get list of flows
            childiter = self._data.plugin_list_store.iter_children(iter)
            while childiter is not None:
                #checkbox is checked
                if self._data.plugin_list_store.get_value(childiter, 0):
                    plugins.append(pname)
                    fname = self._data.plugin_list_store.get_value(
                        childiter, 1)
                    flows.append(fname)

                    #get/set flow params
                    param = self._data.plugin_list_store.get_value(childiter, 3)
                    if param.strip()!="":
                        val = "%s/%s %s" % (pname, fname, param)
                        self._cfg.set("plugin-args",
                                hashlib.sha1(val).hexdigest(), val)
                childiter = self._data.plugin_list_store.iter_next(childiter)

        plugins = map(lambda x: x.encode("string-escape"), plugins)
        flows = map(lambda x: x.encode("string-escape"), flows)

        #set the flow mode
        self._cfg.operation.mode = "flow"
        self._cfg.operation.flow = " ".join(flows)
        self._cfg.operation.plugin = " ".join(plugins)

        self.execute()
        return True

    #results callbacks
    def on_b_ResetResults_activate(self, widget, *args):
        print("on_b_ResetResults_activate")
        self._data.result_list_store.clear()
        del self._data.result_list_iter
        self._data.result_list_iter = dict()
        resetInfo()
        return True

    def on_b_StopResults_activate(self, widget, *args):
        print("on_b_StopResults_activate")
        self._tasker.interrupt()
        widget.set_sensitive(False)
        return True

    def on_start_remote_clicked(self, widget, *args):
        # prepare the config for the remote instances
        c = FAKConfig()
        self.populate_advanced(c)
        
        # write the config
        try:
            fd = open("/tmp/fak_default_remote.cfg", "w")
            c.write(fd)
        except IOError:
            return            

        # start the tests
        self._cfg.operation.mode = "monitor"
        self.execute()
        return True

    def on_edit_nodes_clicked(self, widget, *args):
        l = ListDialog("Remote nodes", "This table lists all remote nodes to start First Aid Kit session on",
                       [],
                       options = {
                           "mode": ListDialog.MODE_TEXT,
                           "key": "Short name",
                           "key-regexp": re.compile("^[a-zA-Z0-9_.-]+$"),
                           "value": "SSH address string",
                           "add": True,
                           "remove": True,
                           "editable-key": True,
                           "abort": False,
                           "default-regexp": "^[A-Za-z0-9._:@-]+( [/A-Za-z0-9 ._-]+)?$",
                           "default-error": "Entry has to have the form of [user@]address[:port] [/cfg/file]"
                           },
                       dir = os.path.dirname(__file__))

        if self._cfg.has_section("remote"):
            for (k, v) in self._cfg.items("remote"):
                l.add(k, v)
        
        res = None
        while res==None or res==gtk.RESPONSE_NONE:
            res = l.run()

        if res==gtk.RESPONSE_ACCEPT:
            #clear remote section
            if self._cfg.has_section("remote"):
                self._cfg.remove_section("remote")
            self._cfg.add_section("remote")

            for (k,v) in l.items():
                if not k or not v:
                    continue
                
                if " " not in v:
                    v = v+" /tmp/fak_default_remote.cfg"
                self._cfg.set("remote", k, v)

            self._data.update_remote()

        l.destroy()        
        return True


    def on_mainmenu_remote_activate(self, widget, *args):
        self._data.remote(True)
        return True

class CallbacksFlagList(object):
    def __init__(self, dialog, cfg, flags):
        self._dialog = dialog
        self._flags = flags
        self._cfg = cfg

    def on_b_OK_activate(self, widget, *args):
        print("on_b_OK_activate")

        f = set()
        for k,w in self._flags.iteritems():
            if w.get_active():
                f.add(k)

        if len(f)==0:
            self._cfg.operation.flags = ""
        else:
            self._cfg.operation.flags = " ".join(
                    map(lambda x: x.encode("string-escape"), f))

        self._dialog.destroy()
        return True

    def on_b_Cancel_activate(self, widget, *args):
        print("on_b_Cancel_activate")
        self._dialog.destroy()
        return True

class ListDialog(object):
    MODE_TEXT = 0
    MODE_CHECKBOX = 1
    MODE_COMBO = 2
    MODE_RADIO = 3
    
    def __init__(self, title, description, items, dir="", options = {}):
        gtkb = gtk.Builder()
        gtkb.add_from_file(os.path.join(dir, "gtk-list.xml"))
        self._dialog = gtkb.get_object("listdialog")
        self._dialog.set_title(title)
        self._options = options

        mode = options.get("mode", 0)

        # text
        if mode == self.MODE_TEXT:
            self._store = gtk.ListStore(gobject.TYPE_STRING, # key
                                    gobject.TYPE_STRING, # textual representation of value
                                    gobject.TYPE_STRING, # raw value
                                    gobject.TYPE_STRING, # tooltip text
                                    gobject.TYPE_PYOBJECT, # regexp object
                                    gobject.TYPE_STRING, # error message
                                    gobject.TYPE_PYOBJECT) # reserved for combo entries

            rend_text_edit = gtk.CellRendererText()
            rend_text_edit.set_property("editable", True)
            rend_text_edit.connect('edited', self.edited_cb, self._store)

            
        # checkboxes
        elif mode == self.MODE_CHECKBOX or mode == self.MODE_RADIO:
            self._store = gtk.ListStore(gobject.TYPE_STRING,
                                    gobject.TYPE_STRING,
                                    gobject.TYPE_BOOLEAN,
                                    gobject.TYPE_STRING,
                                    gobject.TYPE_PYOBJECT,
                                    gobject.TYPE_STRING,
                                    gobject.TYPE_PYOBJECT)

            rend_text_check = gtk.CellRendererToggle()
            rend_text_check.set_radio(mode == self.MODE_RADIO)
            rend_text_check.connect('toggled', self.toggled_cb, self._store)
            rend_text_check.set_property('activatable', True)

        # combo
        elif mode == self.MODE_COMBO:
            self._store = gtk.ListStore(gobject.TYPE_STRING,
                                    gobject.TYPE_STRING,
                                    gobject.TYPE_STRING,
                                    gobject.TYPE_STRING,
                                    gobject.TYPE_PYOBJECT,
                                    gobject.TYPE_STRING,
                                    gtk.ListStore) 
            def _fill(x):
                model = gtk.ListStore(gobject.TYPE_STRING)
                for v in x[6]:
                    model.append((v,))
                return x[:6]+(model,)

            # convert x[6] to list store for combo box
            items = map(_fill, items)

            rend_text_combo = gtk.CellRendererCombo()
            rend_text_combo.set_property("editable", True)
            rend_text_combo.set_property("text-column", 0)
            rend_text_combo.connect('edited', self.edited_cb, self._store)
            rend_text_combo.connect('changed', self.changed_cb, self._store)
            rend_text_combo.set_property('has-entry', True)


        # fill the data store
        map(self._store.append, items)

        self._label = gtkb.get_object("label")
        self._label.set_text(description)
        self._view = gtkb.get_object("view")
        self._view.set_model(self._store)


        # title column
        key_title = options.get("key", "Key")
        if options.get("editable-key", False):
            rend_text_key = gtk.CellRendererText()
            rend_text_key.set_property("editable", True)
            rend_text_key.connect('edited', self.edited_key_cb, self._store)
        else:
            rend_text_key = gtk.CellRendererText()
            
        col_0 = gtk.TreeViewColumn(key_title, rend_text_key, text = 0)
        col_0.set_resizable(True)
        col_0.set_expand(False)

        # value column
        value_title = options.get("value", "Value")
        if mode == self.MODE_TEXT:
            col_1 = gtk.TreeViewColumn(value_title, rend_text_edit, text = 2)
        elif mode == self.MODE_CHECKBOX or mode == self.MODE_RADIO:
            col_1 = gtk.TreeViewColumn(value_title, rend_text_check)
            col_1.add_attribute(rend_text_check, "active", 2)
        elif mode == self.MODE_COMBO:
            col_1 = gtk.TreeViewColumn(value_title, rend_text_combo, text = 2)
            col_1.add_attribute(rend_text_combo, "model", 6)
            
        col_1.set_resizable(True)
        col_1.set_expand(True)
        self._view.append_column(col_0)
        self._view.append_column(col_1)

        gtkb.connect_signals(self)

        self._dialog.show_all()

        if not options.get("back", True):
            gtkb.get_object("back-button").hide()

        if not options.get("abort", True):
            gtkb.get_object("abort-button").hide()

        if mode!=self.MODE_TEXT or not options.get("add", False):
            gtkb.get_object("add-button").hide()

        if mode!=self.MODE_TEXT or not options.get("remove", False):
            gtkb.get_object("remove-button").hide()


    def items(self):
        F = lambda row: (row[0], row[2])
        return map(F, self._store)

    def run(self):
        return self._dialog.run()

    def edited_key_cb(self, cell, path, new_data, store):
        krex = self._options.get("key-regexp", None)
        if krex is None or krex.match(new_data):
            store[path][0] = new_data

    def edited_cb(self, cell, path, new_data, store):
        res = store[path][4].match(new_data)
        if res is not None:
            store[path][2] = new_data
        else:
            err = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK)
            err.set_property("text", store[path][5])
            err.run()
            err.destroy()

    def toggled_cb(self, cell, path, store):
        new = not store[path][2]
        if cell.get_radio():
            i = store.get_iter_first()
            while i:
                store[i][2] = False
                i = store.iter_next(i)
            
        store[path][2] = new

    def changed_cb(self, combo, path, new, store):
        store[path][2] = store[path][6][new][0]

    def destroy(self):
        self._dialog.destroy()

    def cb_ok(self, data):
        self._dialog.response(gtk.RESPONSE_ACCEPT)

    def cb_cancel(self, data):
        self._dialog.response(gtk.RESPONSE_CANCEL)

    def cb_close(self, data):
        self._dialog.response(gtk.RESPONSE_CANCEL)

    def add(self, key = None, value = None):
        i = self._store.append()
        txre = self._options.get("default-regexp", ".*")
        if key:
            self._store.set(i, 0, key)
        if value:
            self._store.set(i, 1, value)
            self._store.set(i, 2, value)
        self._store.set(i, 3, txre)
        self._store.set(i, 4, re.compile(txre))
        self._store.set(i, 5, self._options.get("default-error", "Bad input"))
        return i
        
    def cb_add(self, data):
        i = self.add()
        self._view.scroll_to_cell(self._store.get_path(i))
        self._view.set_cursor(self._store.get_path(i))
        self._dialog.response(gtk.RESPONSE_NONE)

    def cb_remove(self, data):
        sel = self._view.get_selection()
        sel.selected_foreach(lambda model, path, iter: model.remove(iter))
        self._dialog.response(gtk.RESPONSE_NONE)

class MainWindow(object):
    name = "Main FirstAidKit Window"
    _cancel_answer = object()
    _no_answer = object()

    def __init__(self, cfg, info, tasker, importance = logging.INFO, dir=""):
        # initialize threads
        gtk.gdk.threads_init()
        
        self._importance = importance
        self._cfg = cfg
        self._remote = False
        self._glade = gtk.glade.XML(os.path.join(dir, "firstaidkit.glade"),
                "MainWindow")
        self._window = self._glade.get_widget("MainWindow")
        self._cb = CallbacksMainWindow(self._window, cfg, info, tasker, self._glade,
                self)
        self._glade.signal_autoconnect(self._cb)
        self._window.connect("destroy", self._cb.on_destroy)

        self.pages = self._glade.get_widget("pages")
        self.status_text = self._glade.get_widget("status_text")
        self.status_progress = self._glade.get_widget("status_progress")

        self.plugin_list_store = gtk.TreeStore(gobject.TYPE_BOOLEAN,
                gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING,
                gobject.TYPE_STRING)
        self.plugin_list = self._glade.get_widget("tree_Expert")
        self.plugin_list.set_model(self.plugin_list_store)

        self.plugin_rend_text = gtk.CellRendererText()
        self.plugin_rend_text_edit = gtk.CellRendererText()
        self.plugin_rend_text_edit.set_property("editable", True)
        self.plugin_rend_toggle = gtk.CellRendererToggle()
        self.plugin_rend_toggle.set_radio(False)
        self.plugin_rend_toggle.set_property("activatable", False)

        def plugin_rend_text_func(column, cell_renderer, tree_model, iter,
                user_data):
            if tree_model.iter_depth(iter)==0:
                cell_renderer.set_property("cell-background-set", True)
                cell_renderer.set_property("cell-background-gdk",
                        gtk.gdk.Color(red=50000, green=50000, blue=50000))
                cell_renderer.set_property("markup",
                        "<b>" + tree_model.get_value(iter, user_data) + "</b>")
            else:
                cell_renderer.set_property("cell-background-set", False)
                cell_renderer.set_property("text",
                        tree_model.get_value(iter, user_data))
            return

        def plugin_rend_toggle_func(column, cell_renderer, tree_model, iter,
                user_data = None):
            if tree_model.iter_depth(iter)==0:
                cell_renderer.set_property("activatable", False)
                cell_renderer.set_property("active", False)
                cell_renderer.set_property("visible", False)
                cell_renderer.set_property("cell-background-set", True)
                cell_renderer.set_property("cell-background-gdk",
                        gtk.gdk.Color(red=40000, green=40000, blue=40000))
            else:
                cell_renderer.set_property("activatable", True)
                cell_renderer.set_property("active",
                        tree_model.get_value(iter,0))
                cell_renderer.set_property("visible", True)
                cell_renderer.set_property("cell-background-set", False)
            return

        def plugin_rend_toggle_cb(cell, path, data):
            model, col = data
            model[path][col] = not model[path][col]
            return

        def plugin_rend_edited_cb(cell, path, text, data):
            model, col = data
            model[path][col] = text
            return

        self.plugin_list_col_0 = gtk.TreeViewColumn('Use')
        self.plugin_list_col_0.pack_start(self.plugin_rend_toggle, False)
        self.plugin_list_col_0.set_cell_data_func(self.plugin_rend_toggle,
                plugin_rend_toggle_func)
        self.plugin_rend_toggle.connect("toggled", plugin_rend_toggle_cb,
                (self.plugin_list_store, 0))

        self.plugin_list_col_1 = gtk.TreeViewColumn('Name')
        self.plugin_list_col_1.pack_start(self.plugin_rend_text, True)
        self.plugin_list_col_1.set_cell_data_func(self.plugin_rend_text,
                plugin_rend_text_func, 1)

        self.plugin_list_col_2 = gtk.TreeViewColumn('Description')
        self.plugin_list_col_2.pack_start(self.plugin_rend_text, True)
        self.plugin_list_col_2.set_cell_data_func(self.plugin_rend_text,
                plugin_rend_text_func, 2)

        self.plugin_list_col_3 = gtk.TreeViewColumn('Parameters')
        self.plugin_list_col_3.pack_start(self.plugin_rend_text_edit, True)
        self.plugin_list_col_3.set_cell_data_func(self.plugin_rend_text_edit,
                plugin_rend_text_func, 3)
        self.plugin_rend_text_edit.connect("edited", plugin_rend_edited_cb,
                (self.plugin_list_store, 3))

        self.plugin_list.append_column(self.plugin_list_col_0)
        self.plugin_list.append_column(self.plugin_list_col_1)
        self.plugin_list.append_column(self.plugin_list_col_2)
        self.plugin_list.append_column(self.plugin_list_col_3)
        self.plugin_list.set_search_column(1)

        pluginsystem = tasker.pluginsystem()
        self.plugin_iter = {}
        self.flow_list_data = set()

        #flow combobox
        for plname in pluginsystem.list():
            p = pluginsystem.getplugin(plname)
            piter = self.plugin_list_store.append(None,
                    [False, "%s (%s)" % (p.name, p.version), p.description,
                        "", plname])
            self.plugin_iter[plname] = piter
            for n,d in [ (f, p.getFlow(f).description) for f in p.getFlows() ]:
                self.plugin_list_store.append(piter, [False, n, d, "", plname])
                self.flow_list_data.add(n)

        self.flow_list_rend_text = gtk.CellRendererText()
        self.flow_list_store = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.flow_list_store_diagnose = -1
        for idx,n in enumerate(sorted(self.flow_list_data)):
            self.flow_list_store.append([n, pluginsystem.get_title(n)])
            if n=="diagnose":
                self.flow_list_store_diagnose = idx
        self.flow_list = self._glade.get_widget("combo_Advanced_Flows")
        self.flow_list.set_model(self.flow_list_store)
        self.flow_list.pack_start(self.flow_list_rend_text, True)
        self.flow_list.add_attribute(self.flow_list_rend_text, 'text', 1)
        self.flow_list.set_active(self.flow_list_store_diagnose)

        # results
        self.result_list_store = gtk.ListStore(gobject.TYPE_STRING,
                gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_INT, gobject.TYPE_STRING)
        self.result_list = self._glade.get_widget("tree_Results")
        self.result_list.set_model(self.result_list_store)
        self.result_list_iter = {}

        def result_rend_text_func(column, cell_renderer, tree_model, iter,
                (use_state_fg, use_state_bg, col)):
            colors = [
                    None,
                    gtk.gdk.Color(red=40000, green=62000, blue=40000),
                    gtk.gdk.Color(red=62000, green=40000, blue=40000),
                    gtk.gdk.Color(red=50000, green=55000, blue=65500),
                    gtk.gdk.Color(red=0, green=0, blue=0)
                    ]

            state = tree_model.get_value(iter, 3)

            if use_state_fg and state!=2 and state!=0:
                cell_renderer.set_property("foreground-set", True)
                cell_renderer.set_property("foreground-gdk",
                        gtk.gdk.Color(red=50000, green=50000, blue=50000))
            else:
                cell_renderer.set_property("foreground-set", False)

            if colors[state] and use_state_bg:
                cell_renderer.set_property("cell-background-set", True)
                cell_renderer.set_property("cell-background-gdk", colors[state])
                if state==4:
                    cell_renderer.set_property("foreground-set", True)
                    cell_renderer.set_property("foreground-gdk",
                        gtk.gdk.Color(red=65000, green=50000, blue=50000))
            else:
                cell_renderer.set_property("cell-background-set", False)


            cell_renderer.set_property("text",
                    tree_model.get_value(iter, col))
            return

        self.result_rend_text = gtk.CellRendererText()

        def sort_column(col, colid):
            self.result_list_store.set_sort_column_id(colid, gtk.SORT_ASCENDING)

        self.result_list_col_0 = gtk.TreeViewColumn('Name')
        self.result_list_col_0.pack_start(self.result_rend_text, True)
        self.result_list_col_0.set_cell_data_func(self.result_rend_text,
                result_rend_text_func, (False, False, 0))
        self.result_list_col_0.set_property('clickable', True)
        self.result_list_col_0.connect('clicked', sort_column, 0)

        self.result_list_col_1 = gtk.TreeViewColumn('Status')
        self.result_list_col_1.pack_start(self.result_rend_text, True)
        self.result_list_col_1.set_cell_data_func(self.result_rend_text,
                result_rend_text_func, (False, True, 1))
        self.result_list_col_1.set_property('clickable', True)
        self.result_list_col_1.connect('clicked', sort_column, 1)


        self.result_list_col_2 = gtk.TreeViewColumn('Description')
        self.result_list_col_2.pack_start(self.result_rend_text, True)
        self.result_list_col_2.set_cell_data_func(self.result_rend_text,
                result_rend_text_func, (True, False, 2))
        self.result_list_col_2.set_property('clickable', True)

        self.result_list_col_3 = gtk.TreeViewColumn('Status ID')
        self.result_list_col_3.pack_start(self.result_rend_text, True)
        self.result_list_col_3.add_attribute(self.result_rend_text, 'text', 3)
        self.result_list_col_3.set_property("visible", False)

        self.result_list_col_remote = gtk.TreeViewColumn('Node')
        self.result_list_col_remote.pack_start(self.result_rend_text, True)
        self.result_list_col_remote.add_attribute(self.result_rend_text, 'text', 4)
        self.result_list_col_remote.set_property("visible", False)
        self.result_list_col_remote.set_property('clickable', True)
        self.result_list_col_remote.connect('clicked', sort_column, 4)
        
        self.result_list.append_column(self.result_list_col_remote)
        self.result_list.append_column(self.result_list_col_0)
        self.result_list.append_column(self.result_list_col_1)
        self.result_list.append_column(self.result_list_col_2)
        self.result_list.append_column(self.result_list_col_3)
        self.result_list.set_search_column(1)

    def remote(self, enable = True):
        remote_w = self._glade.get_widget("remote_box")
        remote_w.set_property("visible", enable)
        self.result_list_col_remote.set_property("visible", enable)
        self._remote = enable
        if enable:
            self.update_remote()

    def update_remote(self):
        num = 0
        if self._cfg.has_section("remote"):
            num = len(self._cfg.items("remote"))
        remote_count = self._glade.get_widget("node_count")
        remote_count.set_markup("You have configured <b>%d nodes</b>. Press this button to edit the list." % num)

    def refresh(self):
        if self._cfg.has_section("remote"):
            num = len(self._cfg.items("remote"))
        else:
            num = 0
            
        self.remote(num > 0)

    def update(self, mailbox, message):

        def issue_state(self):
            if self._exception or self._error:
                return ("Error", 4)
            elif self._skipped:
                return ("No result", 0)
            elif self._fixed:
                return ("Fixed", 3)
            elif self._happened and self._checked:
                return ("Detected", 2)
            elif self._checked:
                return ("No problem", 1)
            else:
                return ("Waiting for check", 0)

        if message["remote"] and not self._remote:
            self.remote()

        if self._cfg.operation.verbose == "True":
            self._importance = logging.DEBUG
        else:
            self._importance = logging.INFO

        """Read the reporting system message and schedule a call to update
        stuff in the gui using gobject.idle_add(_o, func, params...)"""
        if message["action"]==reporting.END and not message["remote"]:
            gobject.idle_add(_o, self._window.destroy)

        elif message["action"]==reporting.CHOICE_QUESTION:
            gobject.idle_add(_o, self.choice_question, message)

        elif message["action"]==reporting.CONFIG_QUESTION:
            gobject.idle_add(_o, self.config_question, message)

        elif message["action"]==reporting.FILENAME_QUESTION:
            gobject.idle_add(_o, self.filename_question, message)

        elif message["action"]==reporting.PASSWORD_QUESTION and message["message"].confirm:
            gobject.idle_add(_o, self.password_question, message)

        elif message["action"] in (reporting.TEXT_QUESTION, reporting.PASSWORD_QUESTION):
            gobject.idle_add(_o, self.text_question, message)

        elif message["action"]==reporting.START:
            if self._importance<=message["importance"]:
                ctx = self.status_text.get_context_id(message["origin"].name)
                gobject.idle_add(_o, self.status_text.push, ctx,
                        "START: %s (%s)" % (message["origin"].name,
                            message["message"]))

        elif message["action"]==reporting.STOP:
            if self._importance<=message["importance"]:
                ctx = self.status_text.get_context_id(message["origin"].name)
                gobject.idle_add(_o, self.status_text.push, ctx,
                        "STOP: %s (%s)" % (message["origin"].name,
                            message["message"]))

        elif message["action"]==reporting.PROGRESS:
            if self._importance<=message["importance"]:
                if message["message"] is None:
                  gobject.idle_add(self.status_progress.hide)
                else:
                  gobject.idle_add(_o, self.status_progress.set_text,
                          "%d/%d - %s" % (message["message"][0],
                              message["message"][1], message["origin"].name))
                  gobject.idle_add(_o, self.status_progress.set_fraction,
                          float(message["message"][0])/message["message"][1])
                  gobject.idle_add(_o, self.status_progress.show)

        elif message["action"]==reporting.INFO:
            if self._importance<=message["importance"]:
                ctx = self.status_text.get_context_id(message["origin"].name)
                gobject.idle_add(_o, self.status_text.push, ctx,
                        "INFO: %s (%s)" % (message["message"],
                            message["origin"].name))

        elif message["action"]==reporting.ALERT:
            if self._importance<=message["importance"]:
                ctx = self.status_text.get_context_id(message["origin"].name)
                gobject.idle_add(_o, self.status_text.push, ctx,
                        "ALERT: %s (%s)" % (message["message"],
                            message["origin"].name))

        elif message["action"]==reporting.EXCEPTION:
            ctx = self.status_text.get_context_id(message["origin"].name)
            gobject.idle_add(_o, self.status_text.push, ctx,
                    "EXCEPTION: %s (%s)" % (message["message"],
                        message["origin"].name))

        elif message["action"]==reporting.TABLE:
            if self._importance<=message["importance"]:
                print("TABLE %s FROM %s" % (message["title"],
                    message["origin"].name,))
                pprint.pprint(message["message"])

        elif message["action"]==reporting.TREE:
            if self._importance<=message["importance"]:
                print("TREE %s FROM %s" % (message["title"],
                    message["origin"].name,))
                pprint.pprint(message["message"])

        elif message["action"]==reporting.ISSUE:
                i = message["message"]
                iid = i.id
                ctx = self.status_text.get_context_id(message["origin"].name)
                gobject.idle_add(_o, self.status_text.push, ctx,
                    "[%s] %s: %s" % (message["remote_name"], str(i), i.description))
                t,ids = issue_state(i)
                if not self.result_list_iter.has_key(iid):
                    self.result_list_iter[iid] = self.result_list_store.append(
                            [i.name, t, i.description, ids, i.remote_name])
                else:
                    for idx,val in enumerate([i.name, t, i.description, ids, i.remote_name]):
                        gobject.idle_add(_o, self.result_list_store.set,
                                self.result_list_iter[iid], idx, val)

        else:
            print("FIXME: Unknown message action %d!!" % (message["action"],))
            print(message)

    def run(self):
        gtk.gdk.threads_init()
        gtk.gdk.threads_enter()
        gtk.main()
        gtk.gdk.threads_leave()

    def _get_dialog(self, Id):
        dir = os.path.dirname(self._glade.relative_file("."))
        glade = gtk.glade.XML(os.path.join(dir, "firstaidkit.glade"), Id)
        dlg = glade.get_widget(Id)
        return glade, dlg

    def choice_question(self, message):
        """Return the user's answer.

        Return self._no_answer on invalid answer,
        self._cancel_answer if the user wants to cancel.

        """
        try:
            gtk.gdk.threads_enter()
            
            # prepare the dialog content
            glade, dlg = self._get_dialog("ChoiceQuestionDialog")
            question = message["message"]
            glade.get_widget("choice_question_label").set_text(question.prompt)
            vbox = glade.get_widget("choice_question_vbox")
            radio_map = {}
            group = None
            for (value, name) in question.choices:
                r = gtk.RadioButton(group, name, False)
                radio_map[r] = value
                r.show()
                vbox.pack_start(r)
                if group is None:
                    group = r

            # run the dialog and send the response
            while True:
                if dlg.run()!=gtk.RESPONSE_OK:
                    message["reply"].end(level = reporting.FIRSTAIDKIT)
                    break
                else:
                    res = self._no_answer
                    for r in radio_map:
                        if r.get_active():
                            res = radio_map[r]
                            break
                    if res!=self._no_answer:
                        question.send_answer(message, res, origin = self)
                        break
                            
        finally:
            # schedule dialog destroy
            dlg.destroy()
            gtk.gdk.flush()
            gtk.gdk.threads_leave()
                            
    def filename_question(self, message):
        """Return the user's answer.

        Return self._no_answer on invalid answer,
        self._cancel_answer if the user wants to cancel.

        """
        # STOCK_OK is neutral enough so that we don't need to distinguish
        # between "open" and "save" mode for now.
        try:
            gtk.gdk.threads_enter()

            question = message["message"]
            dlg = gtk.FileChooserDialog(title = question.prompt,
                                        parent = self._window,
                                        action = gtk.FILE_CHOOSER_ACTION_SAVE,
                                        buttons = (gtk.STOCK_CANCEL,
                                                   gtk.RESPONSE_REJECT,
                                                   gtk.STOCK_OK,
                                                   gtk.RESPONSE_ACCEPT))
            
            if dlg.run()==gtk.RESPONSE_ACCEPT:
                question.send_answer(message, dlg.get_filename(), origin = self)
            else:
                message["reply"].end(level = reporting.FIRSTAIDKIT)
        finally:
            # schedule dialog destroy
            dlg.destroy()
            gtk.gdk.flush()
            gtk.gdk.threads_leave()
        
    def config_question(self, message):
        """Return the user's answers.

        Return self._no_answer on invalid answer,
        self._cancel_answer if the user wants to cancel.

        """

        try:
            gtk.gdk.threads_enter()

            question = message["message"]
            dlg = ListDialog(title = question.title,
                             description = question.description,
                             items = question.items,
                             dir = os.path.dirname(self._glade.relative_file(".")),
                             options = question.options
                             )

            res = dlg.run()

            if res==gtk.RESPONSE_ACCEPT:
                question.send_answer(message, dlg.items(), origin = self)
            elif res==gtk.RESPONSE_CANCEL:
                question.send_answer(message, [], origin = self)
            elif res==gtk.RESPONSE_DELETE_EVENT:
                question.send_answer(message, [], origin = self)
            elif res==2:
                question.send_answer(message, ReturnBack, origin = self)
            elif res==1:
                question.send_answer(message, ReturnAbort, origin = self)
            else:
                raise Exception("Unknown value %s" % (res,))

        except Exception, e:
            print e
            raise

        finally:
            # schedule dialog destroy
            dlg.destroy()
            gtk.gdk.flush()
            gtk.gdk.threads_leave()

    def text_question(self, message):
        """Return the user's answer.

        Return self._no_answer on invalid answer,
        self._cancel_answer if the user wants to cancel.

        """
        
        try:
            gtk.gdk.threads_enter()
            
            glade, dlg = self._get_dialog("TextQuestionDialog")
            question = message["message"]

            glade.get_widget("text_question_label"). \
                                                     set_text(question.prompt)
            entry = glade.get_widget("text_question_entry")
            if isinstance(question, reporting.PasswordQuestion):
                entry.set_visibility(False)
                
            if dlg.run()==gtk.RESPONSE_OK:
                question.send_answer(message, entry.get_text(), origin = self)
            else:
                message["reply"].end(level = reporting.FIRSTAIDKIT)
        finally:
            # schedule dialog destroy
            dlg.destroy()
            gtk.gdk.flush()
            gtk.gdk.threads_leave()
            
    def password_question(self, message):
        """Return the user's answer.

        Return self._no_answer on invalid answer,
        self._cancel_answer if the user wants to cancel.

        """

        try:
            gtk.gdk.threads_enter()

            glade, dlg = self._get_dialog("TwoPasswordDialog")
            question = message["message"]
            assert question.confirm

            glade.get_widget("two_password_label1"). \
                                                     set_text(question.prompt)
            glade.get_widget("two_password_label2"). \
                                                     set_text("Confirm: %s " % (question.prompt,))
            entry1 = glade.get_widget("two_password_entry1")
            entry2 = glade.get_widget("two_password_entry2")
            while True:
                if dlg.run()!=gtk.RESPONSE_OK:
                    message["reply"].end(level = reporting.FIRSTAIDKIT)
                    break
                elif entry1.get_text()==entry2.get_text():
                    question.send_answer(message, entry1.get_text(), origin = self)
                    break
                else:
                    continue
        finally:
            # schedule dialog destroy
            dlg.destroy()
            gtk.gdk.flush()
            gtk.gdk.threads_leave()

class FlagList(object):
    def __init__(self, cfg, flags, dir=""):
        self._glade = gtk.glade.XML(os.path.join(dir, "firstaidkit.glade"),
                "FlagList")
        self._window = self._glade.get_widget("FlagList")
        self._window.set_modal(True)
        self.flags = {}
        self._cb = CallbacksFlagList(self._window, cfg, self.flags)
        self._glade.signal_autoconnect(self._cb)
        fl_gui = self._glade.get_widget("box_flags")
        flags_set = cfg.operation._list("flags")
        for f in sorted(flags.known()):
            b = gtk.CheckButton(label=f)
            self.flags[f] = b
            b.set_active(f in flags_set)
            b.show()
            fl_gui.pack_start(b, expand=False, fill=True)
        l = gtk.Label("")
        l.show()

        fl_gui.pack_end(l, expand=True, fill=True)

class AboutDialog(object):
    def close(self, widget, *args):
        self._window.destroy()

    def __init__(self, cfg, dir=""):
        self._glade = gtk.glade.XML(os.path.join(dir, "firstaidkit.glade"),
                "AboutDialog")
        self._window = self._glade.get_widget("AboutDialog")
        self._window.connect("response", self.close)

        try:
            cfg = cfg.getConfigBits("about")
            version = cfg.about.version
            license = cfg.about.copying
        except:
            version = "development"
            license = os.path.join(os.path.dirname(dir), "COPYING")

        self._window.set_version(version)
        try:
            self._window.set_license(open(license, "r").read())
        except IOError:
            self._window.set_license(None)

class PluginInfo(object):
    def close(self, widget):
        self._window.destroy()

    def __init__(self, plugin, dir=""):
        self._glade = gtk.glade.XML(os.path.join(dir, "firstaidkit.glade"),
                "PluginInfo")
        self._window = self._glade.get_widget("PluginInfo")
        self._window.set_modal(True)
        self._window.set_title(self._window.get_title()+plugin.name)

        self._close = self._glade.get_widget("CloseButton")
        self._close.connect("clicked", self.close)

        self._name = self._glade.get_widget("Info_name")
        self._name.set_label(plugin.name)

        self._version = self._glade.get_widget("Info_version")
        self._version.set_label(plugin.version)

        self._author = self._glade.get_widget("Info_author")
        self._author.set_label(plugin.author)

        self._description = self._glade.get_widget("Info_description")
        self._description.set_label(plugin.description)

        self._table = self._glade.get_widget("Table")

        for n,d in [ (f, plugin.getFlow(f).description)
                for f in plugin.getFlows() ]:
            if n==plugin.default_flow:
                lname = gtk.Label("<b>"+n+"</b>")
                lname.set_property("use-markup", True)
            else:
                lname = gtk.Label(n)
            lname.show()
            ldesc = gtk.Label(d)
            ldesc.show()
            ldesc.set_line_wrap(True)

            sy = self._table.get_property("n-rows")
            sx = self._table.get_property("n-columns")
            sy += 1
            self._table.resize(sy, sx)
            self._table.attach(lname, 0, 1, sy-1, sy, yoptions = gtk.FILL,
                    xoptions = gtk.FILL)
            lname.set_alignment(0, 0)
            self._table.attach(ldesc, 1, 2, sy-1, sy, yoptions = gtk.FILL,
                    xoptions = gtk.FILL)
            ldesc.set_alignment(0, 0)


if __name__=="__main__":
    w = MainWindow(None, None, None)
    w.run()

