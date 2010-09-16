from blocks.common import BlockRoom
from blocks.v4_base import BlockContainerV4
from other import ScriptBlockContainerV4, ObjectBlockContainerV4

class BlockROV4(BlockRoom, BlockContainerV4): # also globally indexed
    def _init_class_data(self):
        self.name = "RO"
        self.lf_name = "LF"
        self.script_types = frozenset(["EN",
                                  "EX",
                                  "LS"])
        self.object_types = frozenset(["OI",
                                  "OC"])
        self.object_between_types = frozenset(["NL",
                                  "SL"])
        self.object_image_type = "OI"
        self.object_code_type = "OC"
        self.num_scripts_type = "LC"
        self.script_container_class = ScriptBlockContainerV4
        self.object_container_class = ObjectBlockContainerV4
