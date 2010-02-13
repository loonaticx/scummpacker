#! /usr/bin/python
import os
import re
import blocks
from common import *

INDEXED_BLOCKS_V4 = (
    "RO", # rooms
    "LF", # lf
    "SC", # scripts
    "CO", # cosutmes
    "SO", # sounds
)

class BlockDispatcherV4(AbstractBlockDispatcher):

    CRYPT_VALUE = 0x69
    BLOCK_NAME_LENGTH = 2
    BLOCK_MAP = {
       # Container blocks
        "LE" : blocks.BlockContainerV4, # main container (Lucasarts Entertainment)
        "LF" : blocks.BlockLFV4, # contains rooms and global resources
        "RO" : blocks.BlockContainerV4, # room
#
#        # Sound blocks
        "SO" : blocks.BlockSOV4, # sound, also container
#        "WA" : None, # VOC (wave)
#        "AD" : None, # adlib
#
        # Globally indexed blocks
        "SC" : blocks.BlockGloballyIndexedV4, # scripts
        "CO" : blocks.BlockGloballyIndexedV4, # costumes

        # Other blocks that should not use default block functionality
        "FO" : blocks.BlockFOV4, # file (room) offsets
        "LS" : blocks.BlockLSV4, # local scripts
#        "HD" : None, # room header

    }
    REGEX_BLOCKS = [
        #(re.compile(r"IM[0-9]{2}"), blocks.BlockContainerV4)
    ]
    DEFAULT_BLOCK = blocks.BlockDefaultV4
    ROOT_BLOCK = blocks.BlockDefaultV4

    def _read_block_name(self, resource):
        """ SCUMM v3 and v4 stores block size before the block name."""
        resource.seek(4, os.SEEK_CUR)
        bname = resource.read(self.BLOCK_NAME_LENGTH)
        resource.seek(-self.BLOCK_NAME_LENGTH, os.SEEK_CUR)
        resource.seek(-4, os.SEEK_CUR)
        return bname
