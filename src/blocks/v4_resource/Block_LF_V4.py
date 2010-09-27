from blocks.common import BlockLucasartsFile
from blocks.v4_base import BlockContainerV4, BlockGloballyIndexedV4
import scummpacker_control as control
import scummpacker_util as util


class BlockLFV4(BlockLucasartsFile, BlockContainerV4, BlockGloballyIndexedV4):
    is_unknown = False
    disk_lookup_name = "Disk"

    def _read_data(self, resource, start, decrypt, room_start=0):
        """LF blocks store the room number before any child blocks."""
        # NOTE: although we read index in here, it gets overridden in load_from_resource.
        self.index = util.str2int(resource.read(2), crypt_val=(self.crypt_value if decrypt else None))
        end = start + self.size
        while resource.tell() < end:
            block = control.block_dispatcher.dispatch_next_block(resource)
            block.load_from_resource(resource, start)
            self.append(block)

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