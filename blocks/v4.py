#! /usr/bin/python
from __future__ import with_statement
import logging
import os
import xml.etree.ElementTree as et
import scummpacker_control as control
#import scummpacker_util as util
from common import *

class BlockDefaultV4(AbstractBlock):
    def _read_header(self, resource, decrypt):
        # Should be reversed for old format resources
        self.size = self._read_size(resource, decrypt)
        self.name = self._read_name(resource, decrypt)

    def _read_size(self, resource, decrypt):
        size = resource.read(4)
        if decrypt:
            size = util.crypt(size, self.crypt_value)
        return util.str_to_int(size, is_BE=util.LE)

    def _write_header(self, outfile, encrypt):
        size = util.int_to_str(self.size, is_BE=util.LE, crypt_val=(self.crypt_value if encrypt else None))
        outfile.write(size)
        outfile.write(self.name)

    def _write_dummy_header(self, outfile, encrypt):
        """Writes placeholder information (block name, block size of 0)"""
        size = util.int_to_str(0, is_BE=util.LE, crypt_val=(self.crypt_value if encrypt else None))
        outfile.write(size)
        outfile.write(self.name)

class BlockContainerV4(BlockContainer, BlockDefaultV4):
    block_ordering = [
        "LE",
        "FO",

        "LF",
        # Inside LF
        "RO",
         # Inside RO
         "HD", # header
         "CC",
         "SP",
         "BX",
         "PA", # palette
         "SA",
         "BM", # bitmap
         "OI", # object image
         "NL", # ???
         "SL", # ???
         "OC", # object code
         "EX", # exit code
         "EN", # entry code
         "LC", # number of local scripts
         "LS", # local script
        # Inside LF again
        "SC", # script
        "SO", # sound
         # Inside SO
         "WA", # voc
         "AD", # adlib
        "CO", # costume
    ]
    
    junk_locations = {
        63314 : 24, # Loom CD
        3601305 : 24, # Loom CD
    }

    def _read_data(self, resource, start, decrypt):
        """Also, first LF file seems to store (junk?) data after the last child block, at least
        for LOOM CD and Monkey Island 1."""
        logging.debug("Reading children from container block...")
        end = start + self.size
        while resource.tell() < end:
            if resource.tell() in self.junk_locations:
                logging.warning("Skipping known junk data at offset: %d" % resource.tell() )
                resource.seek(self.junk_locations[resource.tell()], os.SEEK_CUR) # skip junk data
            block = control.block_dispatcher.dispatch_next_block(resource)
            block.load_from_resource(resource, start)
            self.append(block)

class BlockLFV4(BlockContainerV4):
    def _read_data(self, resource, start, decrypt):
        """LF blocks store the room number before any child blocks.

        Also, first LF file seems to store (junk?) data after the last child block, at least
        for LOOM CD and Monkey Island 1."""
        logging.debug("Reading children from container block...")
        self.index = util.str_to_int(resource.read(2), crypt_val=(self.crypt_value if decrypt else None))
        super(BlockLFV4, self)._read_data(resource, start, decrypt)

def __test_unpack():
    import dispatchers
    control.global_args.set_args(unpack=True, pack=False, scumm_version="4",
        game="LOOMCD", input_file_name="DISK01.LEC", output_file_name="D:\\TEMP")
    outpath = "D:\\TEMP"

#    dirfile = file("000.LFL", "rb")
#    dir_block = dispatchers.IndexBlockContainerV5()
#    dir_block.load_from_resource(dirfile)
#    dirfile.close()
#
#    dir_block.save_to_file(outpath)
    logging.debug("Reading from resources...")

    control.block_dispatcher = dispatchers.BlockDispatcherV4()
    resfile = file("DISK01.LEC", "rb")
    block = BlockContainerV4(2, 0x69)
    block.load_from_resource(resfile)
    resfile.close()

    logging.debug("Saving to files...")
    block.save_to_file(outpath)

def __test():
    __test_unpack()
    #__test_unpack_from_file()
    #__test_pack()

# TODO: better integration test dispatching
test_blocks_v4 = __test

if __name__ == "__main__": __test()
