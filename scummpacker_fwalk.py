#!/usr/bin/env python
import os
import re

import scummpacker_blocks as blocks

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
                
    def save_to_resource(self, path):
        for c in self.children:
            c.save_to_resource(path)

class RootFileWalkerV5(AbstractFileWalker):
    FILES_TO_FIND = {
        r"LECF" : None
    }
    
class IndexFileWalkerV5(AbstractFileWalker):
    FILES_TO_FIND = {
        r"maxs\.xml" : blocks.BlockMAXSV5,
        r"roomnames\.xml" : blocks.BlockRNAMV5,
        r"DOBJ\.dmp" : blocks.BlockDOBJV5,
        r"DROO\.dmp" : blocks.BlockDefaultV5
    }
    
class FileWalkerLECFV5(AbstractFileWalker):
    FILES_TO_FIND = {
        r"ROOM" : blocks.BlockROOMV5,
        r"SOUN_[0-9]{3}(?:\.dmp)?" : blocks.BlockSOUNV5,
        r"CHAR_[0-9]{3}" : blocks.BlockGloballyIndexedV5,
        r"COST_[0-9]{3}" : blocks.BlockGloballyIndexedV5,
        r"SCRP_[0-9]{3}" : blocks.BlockDefaultV5
    }
    
class FileWalkerROOMV5(AbstractFileWalker):
    FILES_TO_FIND = {
        r"BOXD\.dmp" : blocks.BlockDefaultV5,
        r"BOXM\.dmp" : blocks.BlockDefaultV5,
        r"CLUT\.dmp" : blocks.BlockDefaultV5,
        r"CYCL\.dmp" : blocks.BlockDefaultV5,
        r"EPAL\.dmp" : blocks.BlockDefaultV5,
        r"SCAL\.dmp" : blocks.BlockDefaultV5,
        r"TRNS\.dmp" : blocks.BlockDefaultV5,
        r"header\.xml" : blocks.BlockRMHDV5,
        r"RMIM" : blocks.BlockContainerV5,
        r"objects" : blocks.ObjectBlockContainer,
        r"scripts" : blocks.ScriptBlockContainer
    }
    
class FileWalkerScriptsDirV5(AbstractFileWalker):
    FILES_TO_FIND = {
        r"ENCD\.dmp" : blocks.BlockDefaultV5,
        r"EXCD\.dmp" : blocks.BlockDefaultV5,
        r"LSCR_[0-9]{3}\.dmp" : blocks.BlockLSCRV5
    }
    
class FileWalkerObjectsDirV5(AbstractFileWalker):
    FILES_TO_FIND = {
        r"[0-9]{3}_.*" : None
    }
    
class FileWalkerSingleObjectDirV5(AbstractFileWalker):
    FILES_TO_FIND = {
        r"IM[0-9a-fA-F]{2}" : blocks.BlockContainerV5,
        r"header\.xml" : None,
        r"VERB\.dmp" : None
    }
    
class FileWalkerImageV5(AbstractFileWalker):
    FILES_TO_FIND = {
        r"SMAP\.dmp" : None,
        r"ZP[0-9a-fA-F]{3}\.dmp" : None
    }
