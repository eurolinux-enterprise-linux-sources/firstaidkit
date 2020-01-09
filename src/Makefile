# First Aid Kit - diagnostic and repair tool for Linux
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


NAME := "firstaidkit"
VERSION := $(shell awk '/Version:/ { print $$2 }' firstaidkit.spec)
RELEASE := $(shell awk '/Release:/ { print $$2 }' firstaidkit.spec)
DATADIR := $(shell rpm --eval "%_datadir")

PLUGIN_PATH = plugins
# all the plugins that have a make build to run
PLUGIN_DIRS = 

build: subdirs about

about:
	@echo "[about]" >> etc/firstaidkit/about; \
	echo "version=$(VERSION)" >> etc/firstaidkit/about; \
	echo "copying=$(DATADIR)/doc/$(NAME)-$(VERSION)/COPYING" >> etc/firstaidkit/about

tarball:
	git archive --format=tar --prefix=$(NAME)-$(VERSION)/ HEAD | gzip -9 > $(NAME)-$(VERSION).tar.gz

rpm-all: tarball
	rpmbuild -ta $(NAME)-$(VERSION).tar.gz
	rm -f $(NAME)-$(VERSION).tar.gz

subdirs:
	for d in $(PLUGIN_DIRS); do make -C $(PLUGIN_PATH)/$$d build; [ $$? == 0 ] || exit 1; done

bumpver:
	@MAYORVER=$$(echo $(VERSION) | cut -d . -f 1-2); \
	NEWSUBVER=$$((`echo $(VERSION) | cut -d . -f 3`+1)); \
	sed -i "s/Version:        $(VERSION)/Version:        $$MAYORVER.$$NEWSUBVER/" firstaidkit.spec; \
	sed -i "s/Release:        .*%/Release:        1%/" firstaidkit.spec; \
	sed -i "s/version=.*/version='$$MAYORVER.$$NEWSUBVER',/" setup.py;
	git commit -a -m "Bump version"
	git tag "firstaidkit-$$MAYORVER.$$NEWSUBVER"

newver:
	make bumpver
	make rpm-all
