from blocks.v6_base import BlockContainerV6
from Block_IMHD_V6 import BlockIMHDV6

class BlockOBIMV5(BlockOBIMShared, BlockContainerV6):
    imhd_class = BlockIMHDV6
    container_class = BlockContainerV6
