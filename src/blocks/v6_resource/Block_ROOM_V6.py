from blocks.common import BlockRoom
from blocks.v6_base import BlockContainerV6
from blocks.v5_resource.other import ScriptBlockContainerV5, ObjectBlockContainerV5

class BlockROOMV6(BlockRoom, BlockContainerV6): # also globally indexed
    def _init_class_data(self):
        self.name = "ROOM"
        self.lf_name = "LFLF"
        self.room_offset_name = "LOFF"
        self.script_types = frozenset(["ENCD",
                                  "EXCD",
                                  "LSCR"])
        self.object_types = frozenset(["OBIM",
                                  "OBCD"])
        self.object_between_types = frozenset()
        self.object_image_type = "OBIM"
        self.object_code_type = "OBCD"
        self.num_scripts_type = "NLSC"
        self.script_container_class = ScriptBlockContainerV5
        self.object_container_class = ObjectBlockContainerV5
        self.dodgy_offsets = {}
