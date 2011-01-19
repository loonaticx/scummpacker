
from v5 import *

class BlockDispatcherV6(BlockDispatcherV5):
    pass

class FileDispatcherV6(FileDispatcherV5):
    pass

class IndexBlockContainerV6(IndexBlockContainerV5):
    BLOCK_MAP = dict(FileDispatcherV5.BLOCK_MAP)
#    BLOCK_MAP.update({
#        "SO" : blocks.BlockSOV3
#    })


