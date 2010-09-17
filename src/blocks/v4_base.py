#! /usr/bin/python
from __future__ import with_statement
import logging
import scummpacker_control as control
import scummpacker_util as util
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
        return util.str2int(size, is_BE=util.LE)

    def _write_header(self, outfile, encrypt):
        size = util.int2str(self.size, is_BE=util.LE, crypt_val=(self.crypt_value if encrypt else None))
        outfile.write(size)
        name = util.crypt(self.name, self.crypt_value) if encrypt else self.name
        outfile.write(name)

    def _write_dummy_header(self, outfile, encrypt):
        """Writes placeholder information (block name, block size of 0)"""
        size = util.int2str(0, is_BE=util.LE, crypt_val=(self.crypt_value if encrypt else None))
        outfile.write(size)
        name = util.crypt(self.name, self.crypt_value) if encrypt else self.name
        outfile.write(name)

class BlockGloballyIndexedV4(BlockGloballyIndexed, BlockDefaultV4):
    lf_name = "LF"
    room_name = "RO"

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
         "objects",
         "OI", # object image
         "NL", # ??? num local scripts?
         "SL", # ???
         "OC", # object code
         "EX", # exit code
         "EN", # entry code
         "LC", # number of local scripts?
         "LS", # local script
         "scripts",
        # Inside LF again
        "SC", # script
        "SO", # sound
         # Inside SO
         "WA", # voc
         "AD", # adlib
        "\x00\x00", # junk data
        "CO", # costume
    ]

    # Anyone know what this junk data is?
    junk_locations = {
        63314 : 24, # Loom CD
        3601305 : 24, # Loom CD
    }

    def _read_data(self, resource, start, decrypt):
        """Also, first LF file seems to store (junk?) data after the last child block, at least
        for LOOM CD and Monkey Island 1."""
        #logging.debug("Reading children from container block...")
        end = start + self.size
        while resource.tell() < end:
            if resource.tell() in self.junk_locations:
                logging.warning("Found known junk data at offset: %d" % resource.tell() )
#                block = JunkDataV4(self.block_name_length, self.crypt_value)
#                block.load_from_resource(resource, start)
#                self.append(block)
#                continue
            block = control.block_dispatcher.dispatch_next_block(resource)
            block.load_from_resource(resource, start)
            self.append(block)
            

class BlockIndexDirectoryV4(BlockIndexDirectory, BlockDefaultV4):
    """ Generic index directory """
    DIR_TYPES = {
        "0R" : "RO",
        "0S" : "SC",
        "0N" : "SO",
        "0C" : "CO",
        #"0O" : "OB" # handled specifically.
    }
    MIN_ENTRIES = {
        "LOOMCD" : {
            "0S" : 199,
            "0N" : 199,
            "0C" : 199
        }
    }

    def _read_data(self, resource, start, decrypt):
        num_items = util.str2int(resource.read(2), crypt_val=(self.crypt_value if decrypt else None))
        room_nums = []
        offsets = []
        i = num_items
        while i > 0:
            room_no = util.str2int(resource.read(1), crypt_val=(self.crypt_value if decrypt else None))
            room_nums.append(room_no)
            offset = util.str2int(resource.read(4), crypt_val=(self.crypt_value if decrypt else None))
            offsets.append(offset)
            i -= 1

        for i, key in enumerate(zip(room_nums, offsets)):
            control.global_index_map.map_index(self.DIR_TYPES[self.name], key, i)
        
        #logging.debug("Index for : %s" % self.name)
        #logging.debug(control.global_index_map.items(self.DIR_TYPES[self.name]))

    def _save_table_data(self, resource, num_items, item_map):
        for i in xrange(num_items):
            if not i in item_map:
                # write dummy values for unused item numbers.
                resource.write(util.int2str(0, 1, crypt_val=self.crypt_value))
                resource.write(util.int2str(0, 4, crypt_val=self.crypt_value))
            else:
                room_num, offset = item_map[i]
                resource.write(util.int2str(room_num, 1, crypt_val=self.crypt_value))
                resource.write(util.int2str(offset, 4, crypt_val=self.crypt_value))


class JunkDataV4(BlockDefaultV4):
    """LOOM CD contains junk data after two of the LF blocks.
    This class allows ScummPacker to save this data (so we can
    add it in to the new resource for a bit-identical copy)."""

    #name = "\x00\x00"
    # Special value used to generate file name. Needs to be set by the
    #  containing/parent block.
    #parent_name = ""

    def save_to_resource(self, resource, room_start=0):
        logging.debug("Saving junk data to resource. room_start: %s" % room_start)
        super(JunkDataV4, self).save_to_resource(resource, room_start)

    def generate_file_name(self):
        return "00_junk.dmp"