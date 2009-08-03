import scummpacker_util as util

class IndexCounter(object):
    def __init__(self, *args):
        self.index_map = {}
        for s in args:
            self.index_map[s] = 0

    def reset_counts(self):
        for k in self.index_map:
            self.index_map[K] = 0
    
##    def increment_index(self, index_name):
##        if not index_name in self.index_map:
##            raise util.ScummPackerException("Unrecognised block \"" 
##                                            + str(index_name) 
##                                            + "\" tried to increment a counted index.")
##        self.index_map[index_name] = self.index_map[index_name] + 1
        
##    def get_index(self, index_name):
##        if not index_name in self.index_map:
##            raise util.ScummPackerException("Unrecognised block \"" 
##                                            + str(index_name) 
##                                            + "\" tried to retrieve a counted index.")
##        return self.index_map[index_name]

    
    def get_next_index(self, index_name):
        if not index_name in self.index_map:
            raise util.ScummPackerException("Unrecognised block \"" 
                                            + str(index_name) 
                                            + "\" tried to retrieve a counted index.")
        self.index_map[index_name] = self.index_map[index_name] + 1
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
        self.__setitem__(map_name, key, index)
        
    def __setitem__(self, map_name, key, index):
        if not map_name in self.index_map:
            raise util.ScummPackerException("Unrecognised block \"" 
                                            + str(map_name) 
                                            + "\" tried to store a global index.")
        self.index_map[map_name][key] = index
        
    def get_index(self, map_name, key):
        return self.__getitem__(map_name, key)
    
    def __getitem__(self, map_name, key):
        if not map_name in self.index_map:
            raise util.ScummPackerException("Unrecognised block \"" 
                                            + str(map_name) 
                                            + "\" tried to retrieve a global index.")
        if not key in self.index_map[map_name]:
            raise util.ScummPackerUnrecognisedIndexException("Block \"" 
                                            + str(map_name) 
                                            + "\" tried to retrieve an unrecognised global index \""
                                            + str(key)
                                            + "\".")
        return self.index_map[map_name][key]
    
global_index_map = None
global_index_map = IndexMappingContainer(
    "ROOM",
    "COST",
    "CHAR",
    "SCRP",
    "SOUN",
    "LFLF",
    "RNAM"
)

unknown_blocks_counter = IndexCounter(
    "ROOM",
    "COST",
    "CHAR",
    "SCRP",
    "SOUN",
    "LFLF"
)