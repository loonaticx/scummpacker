import xml.etree.ElementTree as et
import unittest
import os
from blocks.v5_resource import *

class BlockCDHDV5TestCase(unittest.TestCase):
    def setUp(self):
        self.block = BlockCDHDV5(4, 0x69)

    def populate_block(self):
        self.block.x = 1
        self.block.y = 2
        self.block.width = 3
        self.block.height = 4
        self.block.flags = 5
        self.block.parent = 6
        self.block.walk_x = 7
        self.block.walk_y = 8
        self.block.actor_dir = 9

    def test_BlockCDHDV5_generate_xml_node(self):
        root = et.Element("object")
        self.populate_block()

        self.block.generate_xml_node(root)
        expected_values = dict(
            x = "1",
            y = "2",
            width = "3",
            height = "4",
            flags = "0x5",
            parent = "6",
            walk_x = "7",
            walk_y = "8",
            actor_dir = "9",
        )

        code = root.find("code")
        self.assert_(code is not None, "V5 Object Code Header (CDHD) blocks should add a 'code' node to the combined object XML.")

        for k, v in expected_values.items():
            node = code.find(k)
            val = node.text
            self.assertEqual(val, v, "XML value for %s was %s, expected %s" % (k, val, v))

    def test_BlockCDHDV5_load_header_from_xml(self):
        """ This test makes use of a special XML file."""
        path = os.path.join(os.getcwd(), "test", "blocks", "v5_OBHD.xml")
        self.block._load_header_from_xml(path)
        self.assertEqual(self.block.obj_id, 1001)
        self.assertEqual(self.block.x, 1)
        self.assertEqual(self.block.y, 2)
        self.assertEqual(self.block.width, 3)
        self.assertEqual(self.block.height, 4)
        self.assertEqual(self.block.flags, 5)
        self.assertEqual(self.block.parent, 6)
        self.assertEqual(self.block.walk_x, 7)
        self.assertEqual(self.block.walk_y, 8)
        self.assertEqual(self.block.actor_dir, 9)

if __name__ == '__main__':
    unittest.main()