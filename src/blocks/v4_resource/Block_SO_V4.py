import os
import scummpacker_control as control
from blocks.v4_base import BlockContainerV4, BlockGloballyIndexedV4

class BlockSOV4(BlockContainerV4, BlockGloballyIndexedV4):
    name = "SO"

    def save_to_resource(self, resource, room_start=0):
        location = resource.tell()
        room_num = control.global_index_map.get_index("LF", room_start)
        room_offset = control.global_index_map.get_index("RO", room_num)
        control.global_index_map.map_index(self.name,
                                           (room_num, location - room_offset),
                                           self.index)
        super(BlockSOV4, self).save_to_resource(resource, room_start)

    def load_from_file(self, path):
        name = os.path.split(path)[1]
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

    def generate_file_name(self):
        name = (self.name
                + "_"
                + ("unk_" if self.is_unknown else "")
                + str(self.index).zfill(3))
        return name
