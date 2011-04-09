import os
import blocks
from dispatchers.v5 import *

INDEXED_BLOCKS_V6 = (
    "ROOM",
    "COST",
    "CHAR",
    "SCRP",
    "SOUN",
    "LFLF",
    "RNAM",
    "Disk" # for disk spanning info. Could use "LECF"
)

class BlockDispatcherV6(BlockDispatcherV5):
    BLOCK_MAP = dict(BlockDispatcherV5.BLOCK_MAP)
    BLOCK_MAP.update({
        "OBIM" : blocks.BlockOBIMV6,
        "OBCD" : blocks.BlockOBCDV6,
        "LFLF" : blocks.BlockLFLFV6,
        "ROOM" : blocks.BlockROOMV6,
        "PALS" : blocks.BlockContainerV6,
        "WRAP" : blocks.BlockContainerV6
        # OFFS and APAL will use default blocks for now.
    })

class FileDispatcherV6(FileDispatcherV5):
    BLOCK_MAP = dict(FileDispatcherV5.BLOCK_MAP)
    BLOCK_MAP.update({
        "PALS" : blocks.BlockContainerV6,
        "WRAP" : blocks.BlockContainerV6,
        #"OBIM" : blocks.BlockOBIMV6,
        #"OBCD" : blocks.BlockOBCDV6,
        #"LFLF" : blocks.BlockLFLFV6,
        r"objects" : blocks.ObjectBlockContainerV6,
        "ROOM" : blocks.BlockROOMV6,
        "APAL.dmp" : blocks.BlockDefaultV6,
        "OFFS.dmp" : blocks.BlockDefaultV6
    })

class IndexBlockContainerV6(IndexBlockContainerV5):
    debug = True
    BLOCK_MAP = dict(IndexBlockContainerV5.BLOCK_MAP)
    BLOCK_MAP.update({
        "MAXS" : blocks.BlockMAXSV6,
        "AARY" : blocks.BlockAARYV6
    })

    def load_from_file(self, path):
        IndexBlockContainerV5.load_from_file(self, path)

        aary_block = self.BLOCK_MAP["AARY"](self.BLOCK_NAME_LENGTH, self.CRYPT_VALUE)
        aary_block.load_from_file(os.path.join(path, "aary.xml"))
        self.children.append(aary_block)
