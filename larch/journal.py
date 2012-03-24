# Copyright 2012  Lars Wirzenius
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


class Journal(object):

    '''A journal layer on top of a virtual filesystem.
    
    The journal solves the problem of updating on-disk data structures
    atomically. Changes are first written to a journal, and then moved
    from there to the real location. If the program or system crashes,
    the changes can be completed later on, or rolled back, depending
    on what's needed for consistency.
    
    The journal works as follows:
    
    * ``x`` is the real filename
    * ``new/x`` is a new or modified file
    * ``delete/x`` is a deleted file, moved there immediately
    
    Commit does this:
    
    * for every ``delete/x``, remove it
    * for every ``new/x`` except ``new/metadata``, move to ``x``
    * move ``new/metadata`` to ``metadata``
    
    Rollback does this:
    
    * remove every ``new/x``
    * move every ``delete/x`` to ``x``
    
    When a journalled node store is opened, if ``new/metadata`` exists,
    the commit happens. Otherwise a rollback happens. This guarantees
    that the on-disk state is consistent.
    
    '''
    
    def __init__(self, fs):
        self.fs = fs
    
    def metadata_is_pending(self):
        return False

