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


'''A binary search.

This is sort-of similar to the standard library bisect module, but
has a differnt API. Apart from gratuitous differences, it provides
a way to extract the key from a list item rather than using the
list item directly as a key.

'''


def bsearch(array, key, getkey=None):

    '''Binary search in a list.
    
    Return the indexes surrounding the location in the array where
    the searched item is, or where it would be, if it were, but isn't.
    
    Call the return values a and b. If item exists in array, then
    return its index as both a and b. If it does not exist, return
    adjacent values for a and b for the location where the item would
    be. If a is None, then item would come before first item in list.
    If b is None, after last item in list. If both a and b are None,
    the list is empty.
    
    '''

    def helper(lo, hi):
        lokey = getkey(array[lo])
        hikey = getkey(array[hi])
        assert lo <= hi
        while hi - lo >= 2:
            mid = (lo + hi) / 2
            midkey = getkey(array[mid])
            if lokey <= key <= midkey:
                hi = mid
                hikey = midkey
            else:
                assert midkey <= key <= hikey
                lo = mid
                lokey = midkey

        assert (lo == hi) or (lo+1 == hi)
        assert getkey(array[lo]) == lokey
        assert getkey(array[hi]) == hikey
        if key == lokey:
            return lo, lo
        elif key == hikey:
            return hi, hi
        else:
            assert lo+1 == hi
            return lo, hi


    getkey = getkey or (lambda x: x)
    lo = 0
    hi = len(array) - 1
    if not array:
        return None, None
    elif key < getkey(array[lo]):
        return None, lo
    elif key > getkey(array[hi]):
        return hi, None
    else:
        assert getkey(array[lo]) <= key <= getkey(array[hi])
        return helper(lo, hi)
