from blocks.common import BlockLucasartsFile
from blocks.v4_base import BlockContainerV4, BlockGloballyIndexedV4
import scummpacker_util as util
import logging

class BlockLFV4(BlockLucasartsFile, BlockContainerV4, BlockGloballyIndexedV4):
    is_unknown = False

    def _read_data(self, resource, start, decrypt):
        """LF blocks store the room number before any child blocks.

        Also, first LF file seems to sometimes store (junk?) data after the last child block, at least
        for LOOM CD and Monkey Island 1."""
        logging.debug("Reading LF's children from container block...")
        # NOTE: although we read index in here, it gets overridden in load_from_resource.
        self.index = util.str2int(resource.read(2), crypt_val=(self.crypt_value if decrypt else None))
        super(BlockLFV4, self)._read_data(resource, start, decrypt)
