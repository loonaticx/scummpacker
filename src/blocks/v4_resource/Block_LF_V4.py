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
        #logging.debug("Reading LF's children from container block...")
        # NOTE: although we read index in here, it gets overridden in load_from_resource.
        self.index = util.str2int(resource.read(2), crypt_val=(self.crypt_value if decrypt else None))
        super(BlockLFV4, self)._read_data(resource, start, decrypt)

    def _write_header(self, outfile, encrypt):
        """ Store the room number as part of the header (a bit rude, but keeps code clean-ish)"""
        super(BlockLFV4, self)._write_header(outfile, encrypt)
        self._write_lf_index(outfile, encrypt)

    def _write_dummy_header(self, outfile, encrypt):
        """Writes placeholder information (block name, block size of 0)"""
        super(BlockLFV4, self)._write_dummy_header(outfile, encrypt)
        self._write_lf_index(outfile, encrypt)
        
    def _write_lf_index(self, outfile, encrypt):
        lf_num = util.int2str(self.index, 2, util.LE, crypt_val=self.crypt_value if encrypt else None)
        outfile.write(lf_num)