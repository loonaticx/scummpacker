from blocks.v5_base import BlockDefaultV5, BlockContainerV5
from Block_CDHD_V5 import BlockCDHDV5
from Block_OBNA_V5 import BlockOBNAV5

class BlockOBCDV5(BlockContainerV5):
    name = "OBCD"

    def _read_data(self, resource, start, decrypt):
        end = start + self.size
        block = BlockCDHDV5(self.block_name_length, self.crypt_value)
        block.load_from_resource(resource)
        self.obj_id = block.obj_id # maybe should handle header info better
        self.cdhd = block

        block = BlockDefaultV5(self.block_name_length, self.crypt_value)
        block.load_from_resource(resource)
        self.verb = block

        block = BlockOBNAV5(self.block_name_length, self.crypt_value)
        block.load_from_resource(resource)
        self.obna = block

        self.obj_name = self.obna.obj_name # cheat

    def load_from_file(self, path):
        self.name = "OBCD"
        block = BlockCDHDV5(self.block_name_length, self.crypt_value)
        block.load_from_file(os.path.join(path, "OBHD.xml"))
        self.obj_id = block.obj_id # maybe should handle header info better
        self.cdhd = block

        block = BlockDefaultV5(self.block_name_length, self.crypt_value)
        block.load_from_file(os.path.join(path, "VERB.dmp")) # hmm
        self.verb = block

        block = BlockOBNAV5(self.block_name_length, self.crypt_value)
        block.load_from_file(os.path.join(path, "OBHD.xml"))
        self.obna = block

        self.obj_name = self.obna.obj_name # cheat

    def save_to_file(self, path):
        self.verb.save_to_file(path)

    def save_to_resource(self, resource, room_start=0):
        start = resource.tell()
        self._write_dummy_header(resource, True)
        self.cdhd.save_to_resource(resource, room_start)
        self.verb.save_to_resource(resource, room_start)
        self.obna.save_to_resource(resource, room_start)
        end = resource.tell()
        self.size = end - start
        resource.flush()
        # Go back and write the correct header information
        resource.seek(start, os.SEEK_SET)
        self._write_header(resource, True)
        resource.flush()
        resource.seek(end, os.SEEK_SET) # resume where we left off

    def generate_file_name(self):
        return str(self.obj_id) + "_" + self.obj_name

    def generate_xml_node(self, parent_node):
        self.cdhd.generate_xml_node(parent_node)