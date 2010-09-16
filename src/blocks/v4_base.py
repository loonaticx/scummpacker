#! /usr/bin/python
from __future__ import with_statement
import logging
import os
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
                logging.warning("Skipping known junk data at offset: %d" % resource.tell() )
                resource.seek(self.junk_locations[resource.tell()], os.SEEK_CUR) # skip junk data
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
            "0S" : 199, # TODO: found out right values
            "0N" : 150, # TODO: found out right values
            "0C" : 150  # TODO: found out right values
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
