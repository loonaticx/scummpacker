import os
import xml.etree.ElementTree as et
import scummpacker_util as util
from v5_base import BlockDefaultV5

class BlockMAXSV6(BlockDefaultV5):
    name = "MAXS"
    xml_structure = (
        ("variables", 'i', 'num_vars'),
        ("unknown_1", 'i', 'unknown_1'),
        ("bit_variables", 'i', 'bit_vars'),
        ("local_objects", 'i', 'local_objects'),
        ("arrays", 'i', 'num_arrays'),
        ("unknown_2", 'i', 'unknown_2'),
        ("verbs", 'i', 'verbs'),
        ("floating_objects", 'i', 'floating_objects'),
        ("inventory_objects", 'i', 'inventory_objects'),
        ("rooms", 'i', 'rooms'),
        ("scripts", 'i', 'scripts'),
        ("sounds", 'i', 'sounds'),
        ("character_sets", 'i', 'char_sets'),
        ("costumes", 'i', 'costumes'),
        ("global_objects", 'i', 'global_objects')
    )
    struct_data = {
        'size' : 30,
        'format' : "<15H",
        'attributes' : 
            ('num_vars',
            'unknown_1',
            'bit_vars',
            'local_objects',
            'num_arrays',
            'unknown_2',
            'verbs',
            'floating_objects',
            'inventory_objects',
            'rooms',
            'scripts',
            'sounds',
            'char_sets',
            'costumes',
            'global_objects')
    }

    def _read_data(self, resource, start, decrypt, room_start=0):
        """
        Block Name	   (4 bytes)
        Block Size	   (4 bytes BE)
        Variables	   (2 bytes)
        Unknown	   (2 bytes)
        Bit Variables	   (2 bytes)
        Local Objects	   (2 bytes)
        Arrays		   (2 bytes)
        Unknown	   (2 bytes)
        Verbs		   (2 bytes)
        Floating Objects  (2 bytes)
        Inventory Objects (2 bytes)
        Rooms		   (2 bytes)
        Scripts	   (2 bytes)
        Sounds  	   (2 bytes)
        Character Sets	   (2 bytes)
        Costumes	   (2 bytes)
        Global Objects	   (2 bytes)
        """
        self.read_struct_data(resource, decrypt)

    def save_to_file(self, path):
        root = et.Element("maximums")

        self.generate_xml_node(root)

        util.indent_elementtree(root)
        et.ElementTree(root).write(os.path.join(path, "maxs.xml"))

    def load_from_file(self, path):
        self.size = 30 + self.block_name_length + 4
        self._load_header_from_xml(path)

    def _load_header_from_xml(self, path):
        tree = et.parse(path)
        root = tree.getroot()

        self.read_xml_node(root)

    def _write_data(self, resource, encrypt):
        """ Assumes it's writing to a resource."""
        self.write_struct_data(resource, encrypt)