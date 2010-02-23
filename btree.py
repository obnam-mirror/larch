class LeafNode(object):

    def __init__(self, key, value):
        self.key = key
        self.value = value
        

class IndexNode(object):

    def __init__(self, child1, child2):
        self.child1 = child1
        self.child2 = child2
