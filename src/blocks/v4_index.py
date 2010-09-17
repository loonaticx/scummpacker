#! /usr/bin/python
from v4_base import *

class BlockRNV4(BlockRoomNames, BlockDefaultV4):
    """ Room names """
    name = "RN"

class Block0RV4(BlockRoomIndexes, BlockDefaultV4):
    """ Directory of Rooms.

    Each game seems to have a different padding length.
    
    Doesn't seem to be used in LOOM CD.

    TODO: load a separate "disk/room mapping" XML file."""
    name = "0R"
    DEFAULT_PADDING_LENGTHS = {
        "LOOMCD" : 99
    }
    default_disk_or_room_number = 1
    default_offset = 0

    def save_to_resource(self, resource, room_start=0):
        """0R blocks do not seem to be used in V4 games, so save dummy info."""
        table_entry_length = 5
        num_items_length = 2
        block_size_length = 4
        self.size = (table_entry_length * self.padding_length) + \
                    num_items_length + self.block_name_length + block_size_length
        self._write_header(resource, True)
        resource.write(util.int2str(self.padding_length, 2, crypt_val=self.crypt_value))
        for _ in xrange(self.padding_length): # this is "file/disk number" rather than "room number" in V4
            resource.write(util.int2str(self.default_disk_or_room_number, 1, crypt_val=self.crypt_value))
            resource.write(util.int2str(self.default_offset, 4, crypt_val=self.crypt_value))
    
class Block0OV4(BlockObjectIndexes, BlockDefaultV4):
    name = "0O"
    class_data_size = 3

    def _read_data(self, resource, start, decrypt):
        num_items = util.str2int(resource.read(2), crypt_val=(self.crypt_value if decrypt else None))
        self.objects = []
        # Read all owner+state and class data values
        for _ in xrange(num_items):
            class_data = util.str2int(resource.read(self.class_data_size), util.LE, crypt_val=(self.crypt_value if decrypt else None))            
            owner_and_state = util.str2int(resource.read(1), crypt_val=(self.crypt_value if decrypt else None))
            owner = (owner_and_state & 0xF0) >> 4
            state = owner_and_state & 0x0F            
            self.objects.append([owner, state, class_data])

    def _save_table_data(self, resource):
        for owner, state, class_data in self.objects:
            resource.write(util.int2str(class_data, self.class_data_size, util.LE, crypt_val=self.crypt_value))            
            combined_val = ((owner & 0x0F) << 4) | (state & 0x0F)
            resource.write(util.int2str(combined_val, 1, crypt_val=self.crypt_value))
            
