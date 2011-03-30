import blocks
from v5 import *

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
    debug = True
    BLOCK_MAP = dict(BlockDispatcherV5.BLOCK_MAP)
    BLOCK_MAP.update({
        "LFLF" : blocks.BlockLFLFV6,
        "ROOM" : blocks.BlockROOMV6,
        "PALS" : blocks.BlockContainerV6,
        "WRAP" : blocks.BlockContainerV6
        # OFFS and APAL will use default blocks for now.
    })

class FileDispatcherV6(FileDispatcherV5):
    pass

class IndexBlockContainerV6(IndexBlockContainerV5):
    debug = True
    BLOCK_MAP = dict(IndexBlockContainerV5.BLOCK_MAP)
    BLOCK_MAP.update({
        "MAXS" : blocks.BlockMAXSV6,
        "AARY" : blocks.BlockAARYV6
    })


