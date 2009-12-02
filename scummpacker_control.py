import scummpacker_util as util

class IndexCounter(object):
    def __init__(self, *args):
        self.index_map = {}
        for s in args:
            self.index_map[s] = 0

    def reset_counts(self):
        for k in self.index_map:
            self.index_map[k] = 0
    
    def get_next_index(self, index_name):
        if not index_name in self.index_map:
            raise util.ScummPackerException("Unrecognised block \"" 
                                            + str(index_name) 
                                            + "\" tried to retrieve a counted index.")
        self.index_map[index_name] = self.index_map[index_name] + 1
        return self.index_map[index_name]


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

    def items(self, map_name):
        """Returns key/value pairs for the desired block table."""
        if not map_name in self.index_map:
            raise util.ScummPackerException("Unrecognised block \""
                                            + str(map_name)
                                            + "\" tried to retrieve a global index.")
        return self.index_map[map_name].items()
    
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