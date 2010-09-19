import os
import scummpacker_util as util
import scummpacker_control as control
from blocks.v5_base import BlockContainerV5, BlockGloballyIndexedV5

class BlockSOUNV5(BlockContainerV5, BlockGloballyIndexedV5):
    """ SOUN blocks in V5 may contain CD track data. Unfortunately, these CD
    blocks have no nice header value to look for. Instead, we have to check
    the file size somehow."""

    # Potential task: do some crazy class mutation if this is a CD track.

    name = "SOUN"
    lf_name = "LFLF"
    room_offset_name = "LOFF"

    def __init__(self, *args, **kwds):
        super(BlockSOUNV5, self).__init__(*args, **kwds)
        self.is_cd_track = False

    def _read_data(self, resource, start, decrypt):
        # Not a great way of checking this, since we will try to interpret legit
        # block names as a number.
        # cd_block_size should always be 24 if it's CD track block.
        cd_block_size = util.str2int(resource.read(4), crypt_val=(self.crypt_value if decrypt else None))
        resource.seek(-4, os.SEEK_CUR) # rewind
        if cd_block_size == self.size - 8: # could just check if size == 32, but that might impact legit small blocks
            self.data = self._read_raw_data(resource, self.size - (resource.tell() - start), decrypt)
            self.is_cd_track = True
        else:
            end = start + self.size
            while resource.tell() < end:
                block = control.block_dispatcher.dispatch_next_block(resource)
                block.load_from_resource(resource)
                self.append(block)

    def save_to_file(self, path):
        if self.is_cd_track:
            outfile = file(os.path.join(path, self.generate_file_name()), 'wb')
            self._write_header(outfile, False)
            self._write_raw_data(outfile, False)
            outfile.close()
        else:
            newpath = self._create_directory(path)
            self._save_children(newpath)

    def save_to_resource(self, resource, room_start=0):
        location = resource.tell()
        room_num = control.global_index_map.get_index(self.lf_name, room_start)
        room_offset = control.global_index_map.get_index(self.room_offset_name, room_num)
        control.global_index_map.map_index(self.name,
                                           (room_num, location - room_offset),
                                           self.index)
        if self.is_cd_track:
            self._write_header(resource, self.data, True)
            self._write_raw_data(resource, self.data, True)
        else:
            super(BlockSOUNV5, self).save_to_resource(resource, room_start)

    def load_from_file(self, path):
        name = os.path.split(path)[1]
        if os.path.splitext(name)[1] == '':
            self.is_cd_track = False
            self.name = name.split('_')[0]
            self.index = int(name.split('_')[1])
            self.children = []

            file_list = os.listdir(path)

            for f in file_list:
                b = control.file_dispatcher.dispatch_next_block(f)
                if b != None:
                    b.load_from_file(os.path.join(path, f))
                    self.append(b)
        else:
            self.is_cd_track = True
            self.name = name.split('_')[0]
            self.index = int(os.path.splitext(name.split('_')[1])[0])
            self.children = []
            soun_file = file(path, 'rb')
            self._read_header(soun_file, False)
            self._read_data(soun_file, 0, False)
            soun_file.close()

    def generate_file_name(self):
        name = (self.name
                + "_"
                + ("unk_" if self.is_unknown else "")
                + str(self.index).zfill(3))
        if self.is_cd_track:
            return name + ".dmp"
        else:
            return name
