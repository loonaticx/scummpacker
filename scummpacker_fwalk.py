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
        r"LECF" : None
    }
    
class IndexFileWalkerV5(AbstractFileWalker):
    FILES_TO_FIND = {
        r"maxs\.xml" : None,
        r"roomnames\.xml" : None,
        r"DOBJ\.dmp" : None,
        r"DROO\.dmp" : None
    }
    
class FileWalkerLECFV5(AbstractFileWalker):
    FILES_TO_FIND = {
        r"ROOM" : None,
        r"SOUN_[0-9]{3}(?:\.dmp)?" : None,
        r"CHAR_[0-9]{3}" : None,
        r"COST_[0-9]{3}" : None,
        r"SCRP_[0-9]{3}" : None
    }
    
class FileWalkerROOMV5(AbstractFileWalker):
    FILES_TO_FIND = {
        r"BOXD\.dmp" : None,
        r"BOXM\.dmp" : None,
        r"CLUT\.dmp" : None,
        r"CYCL\.dmp" : None,
        r"EPAL\.dmp" : None,
        r"SCAL\.dmp" : None,
        r"TRNS\.dmp" : None,
        r"header\.xml" : None,
        r"RMIM" : None,
        r"objects" : None,
        r"scripts" : None
    }
    
class FileWalkerScriptsDirV5(AbstractFileWalker):
    FILES_TO_FIND = {
        r"ENCD\.dmp" : None,
        r"EXCD\.dmp" : None,
        r"LSCR_[0-9]{3}\.dmp" : None
    }
    
class FileWalkerObjectsDirV5(AbstractFileWalker):
    FILES_TO_FIND = {
        r"[0-9]{3}_.*" : None
    }
    
class FileWalkerSingleObjectDirV5(AbstractFileWalker):
    FILES_TO_FIND = {
        r"IM[0-9a-fA-F]{2}" : None,
        r"header\.xml" : None,
        r"VERB\.dmp" : None
    }
    
class FileWalkerImageV5(AbstractFileWalker):
    FILES_TO_FIND = {
        r"SMAP\.dmp" : None,
        r"ZP[0-9a-fA-F]{3}\.dmp" : None
    }