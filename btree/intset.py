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


class IntSet(object):

    '''A dense set of integers.

    This is like a plain set, except all values must be integers, and
    there are two additional methods for encoding the set as a text
    string, and decoding from that representation.

    There is also a new property, max, which contains the largest
    value in the set, or None for an empty set.

    '''

    def __init__(self, iterable=None):
        self.ranges = []
        for item in iterable or []:
            self.add(item)

    @property
    def max(self):
        '''Maximum value in set, or None for empty set.'''
        if self.ranges:
            return self.ranges[-1][1]
        else:
            return None

    def __eq__(self, other):
        return self.ranges == other

    def __len__(self):
        return sum(hi-lo+1 for lo, hi in self.ranges)

    def add(self, item):
        for i, (lo, hi) in enumerate(self.ranges):
            if item+1 < lo:
                self.ranges.insert(i, (item, item))
                break
            elif item+1 == lo:
                self.ranges[i] = (item, hi)
                break
            elif lo <= item <= hi:
                break
            elif item-1 == hi and i+1 == len(self.ranges):
                self.ranges[i] = (lo, item)
                break
            elif item-1 == hi and item+1 == self.ranges[i+1][0]:
                lo2, hi2 = self.ranges[i+1]
                self.ranges[i:i+2] = [(lo, hi2)]
                break
        else:
            self.ranges.append((item, item))

    def __str__(self):
        parts = []
        for lo, hi in self.ranges:
            if lo == hi:
                parts.append('%d' % lo)
            else:
                parts.append('%d-%d' % (lo, hi))
        return ','.join(parts)

    def update_from_string(self, string):
        '''Add values from an IntSet represented as a string.'''
        if string:
            for part in string.split(','):
                if '-' in part:
                    lo, hi = part.split('-')
                    for i in range(int(lo), int(hi)+1):
                        self.add(i)
                else:
                    self.add(int(part))

