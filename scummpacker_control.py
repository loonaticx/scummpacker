import scummbler_util as util

class IndexCounter(object):
    def __init__(self, *args):
        self.index_map = {}
        for s in args:
            self.index_map[s] = 0

    def reset_counts(self):
        for k in self.index_map:
            self.index_map[K] = 0
    
    def increment_index(self, index_name):
        self.index_map[index_name] = self.index_map[index_name] + 1
        
    def get_index(self, index_name):
        return self.index_map[index_name]
        

#global_index_counter = None
#global_index_counter = IndexCounter(
#    "ROOM",
#    "COST",
#    "CHAR",
#    "SCRP",
#    "SOUN",
#)

class IndexMappingContainer(object):
    def __init__(self, *args):
        self.index_map = {}
        for s in args:
            self.index_map[s] = {}
    
    def reset_maps(self):
        for k in self.index_map:
            self.index_map[k].clear()
            
    def map_index(self, map_name, key, index):
        self.index_map[map_name][key] = index
        
    def get_index(self, map_name, key):
        return self.index_map[map_name][key]
    
global_index_map = None
global_index_map = IndexMappingContainer(
    "ROOM",
    "COST",
    "CHAR",
    "SCRP",
    "SOUN",
)