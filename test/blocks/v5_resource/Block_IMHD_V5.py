import xml.etree.ElementTree as et
import unittest
import os
from blocks.v5_resource import *

class BlockIMHDV5TestCase(unittest.TestCase):
    def setUp(self):
        self.block = BlockIMHDV5(4, 0x69)

    def populate_block(self):
        self.block.x = 1
        self.block.y = 2
        self.block.width = 3
        self.block.height = 4
        self.block.flags = 5
        self.block.unknown = 6
        self.block.num_imnn = 7
        self.block.num_zpnn = 8

    def test_BlockIMHDV5_generate_xml_node(self):
        root = et.Element("object")
        self.populate_block()

        self.block.generate_xml_node(root)
        expected_values = dict(
            x = "1",
            y = "2",
            width = "3",
            height = "4",
            flags = "0x5",
            unknown = "0x6",
            num_images = "7",
            num_zplanes = "8"
        )

        code = root.find("image")
        self.assert_(code is not None, "V5 Object Image Header IMHD blocks should add a 'image' node to the combined object XML.")

        for k, v in expected_values.items():
            node = code.find(k)
            val = node.text
            self.assertEqual(val, v, "XML value for %s was %s, expected %s" % (k, val, v))

    def test_BlockIMHDV5_load_header_from_xml(self):
        """ This test makes use of a special XML file."""
        path = os.path.join(os.getcwd(), "test", "blocks", "v5_OBHD.xml")
        self.block._load_header_from_xml(path)
        self.assertEqual(self.block.obj_id, 1001)
        self.assertEqual(self.block.x, 1)
        self.assertEqual(self.block.y, 2)
        self.assertEqual(self.block.width, 3)
        self.assertEqual(self.block.height, 4)
        self.assertEqual(self.block.flags, 5)
        self.assertEqual(self.block.unknown, 6)
        self.assertEqual(self.block.num_imnn, 7)
        self.assertEqual(self.block.num_zpnn, 8)

if __name__ == '__main__':
    unittest.main()
