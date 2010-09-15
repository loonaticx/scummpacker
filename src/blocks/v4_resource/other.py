from blocks.common import ObjectBlockContainer, ScriptBlockContainer
from Block_OC_V4 import BlockOCV4
from Block_OI_V4 import BlockOIV4

#--------------------
# Meta or container blocks.
class ObjectBlockContainerV4(ObjectBlockContainer):
    def _init_class_data(self):
        self.obcd_name = "OC"
        self.obim_name = "OI"
        self.obcd_class = BlockOCV4
        self.obim_class = BlockOIV4

class ScriptBlockContainerV4(ScriptBlockContainer):
    local_scripts_name = "LS"
    entry_script_name = "EN"
    exit_script_name = "EX"
    lf_name = "LF"
    num_local_name = "LC" # I used to have this as NL, not sure why.
