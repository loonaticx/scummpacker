#!/usr/bin/env python
import os
import re

class AbstractFileWalker(object):
    # Map regular expressions to block types
    FILES_TO_FIND = {
        
    }
    
    def __init__(self, *args, **kwds):
        super(AbstractFileWalker, self).__init__(*args, **kwds)
        self.children = []
    
    def walk_path(self, path):
        file_list = os.listdir(path)
        # For all file namings we know about, try to create a block and load the
        #  block into memory, interpreting the data from the file.
        for file_re in self.FILES_TO_FIND.keys():
            re_pattern = re.compile(file_re)
            known_files = [f for f in file_list if re_pattern.match(f) != None]
            for kf in known_files:
                block_type = self.FILES_TO_FIND[kf]
                block = block_type(self.BLOCK_NAME_LENGTH, self.CRYPT_VALUE)
                block.load_from_file(kf)
                self.children.append(block)

class RootFileWalkerV5(AbstractFileWalker):
    FILES_TO_FIND = {
        "LECF" : None
    }
    
class IndexFileWalkerV5(AbstractFileWalker):
    FILES_TO_FIND = {
        "maxs.xml" : None,
        "roomnames.xml" : None,
        "DOBJ.dmp" : None,
        "DROO.dmp" : None
    }
    
class FileWalkerLECFV5(AbstractFileWalker):
    FILES_TO_FIND = {
        "ROOM" : None,
        "SOUN_[0-9]{3}(?:.dmp)?" : None,
        "CHAR_[0-9]{3}" : None,
        "COST_[0-9]{3}" : None,
        "_[0-9]{3}" : None
    }