# Makefile
#
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
#
#

PYVER  := $(shell python -c 'import sys; print sys.version[0:3]')
PYTHON = python$(PYVER)
PYTHONINCLUDE = /usr/include/$(PYTHON)


CFLAGS =  -I$(PYTHONINCLUDE)

PYMODULE = _undelpart.so

#Build with libparted (parted-1.8.3 and higher have a pkg-config file)
LDFLAGS = $(shell pkg-config --libs libparted)

build:
	$(CC) $(CFLAGS) -shared -fPIC -o _undelpart.so _undelpart.c $(LDFLAGS)

clean:
	rm -f _undelpart.so *.pyc
