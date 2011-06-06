# Makefile for B-tree implementation
# Copyright 2010  Lars Wirzenius
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


all:
	$(MAKE) -C doc html

check: all
	python -m CoverageTestRunner --ignore-missing-from=without-tests
	rm .coverage
	./insert-remove-test tempdir 100
	rm -r tempdir larch.log
	
clean:
	rm -f .coverage *.py[co] larch/*.py[co] insert.prof lookup.prof
	rm -rf build tempdir larch.log example.tree
	$(MAKE) -C doc clean
