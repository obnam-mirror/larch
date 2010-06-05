def bsearch(array, key, getkey=None):

    def helper(lo, hi):
        lokey = getkey(array[lo])
        hikey = getkey(array[hi])

        mid = (lo + hi) / 2
        midkey = getkey(array[mid])

        if key == lokey:
            return lo, lo
        elif key == hikey:
            return hi, hi
        elif key == midkey:
            return mid, mid
        elif (hi-lo) == 1:
            return lo, hi
        elif lokey < key < midkey:
            return helper(lo, mid)
        else:
            assert midkey < key < hikey
            return helper(mid, hi)

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

