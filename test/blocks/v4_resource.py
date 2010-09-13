import xml.etree.ElementTree as et
import unittest
import os
from blocks.v4_resource import *

class BlockOCV4TestCase(unittest.TestCase):
    def setUp(self):
        self.block = BlockOCV4(2, 0x69)

    def populate_block(self):
        self.block.x = 1
        self.block.y = 2
        self.block.width = 3
        self.block.height = 4
        self.block.unknown = 5
        self.block.parent_state = 6
        self.block.parent = 7
        self.block.walk_x = 8
        self.block.walk_y = 9

    def test_BlockOCV4_generate_xml_node(self):
        root = et.Element("object")
        self.populate_block()

        self.block.generate_xml_node(root)
        expected_values = dict(
            x = "1",
            y = "2",
            width = "3",
            height = "4",
            unknown = "0x5",
            parent_state = "0x6",
            parent = "0x7",
            walk_x = "8",
            walk_y = "9"
        )

        code = root.find("code")
        self.assert_(code is not None, "V4 Object Code blocks should add a 'code' node to the combined object XML.")

        for k, v in expected_values.items():
            node = code.find(k)
            val = node.text
            self.assertEqual(val, v, "XML value for %s was %s, expected %s" % (k, val, v))

    def test_BlockOCV4_load_header_from_xml(self):
        """ This test makes use of a special XML file."""
        path = os.path.join(os.getcwd(), "test", "blocks", "v4_OBHD.xml")
        self.block._load_header_from_xml(path)
        self.assertEqual(self.block.obj_id, 1001)
        self.assertEqual(self.block.x, 1)
        self.assertEqual(self.block.y, 2)
        self.assertEqual(self.block.width, 3)
        self.assertEqual(self.block.height, 4)
        self.assertEqual(self.block.unknown, 5)
        self.assertEqual(self.block.parent_state, 6)
        self.assertEqual(self.block.parent, 7)
        self.assertEqual(self.block.walk_x, 8)
        self.assertEqual(self.block.walk_y, 9)


class BlockOIV4TestCase(unittest.TestCase):
    def setUp(self):
        self.block = BlockOIV4(2, 0x69)

    def populate_block(self):
        pass

    def test_BlockOIV4_generate_xml_node(self):
        root = et.Element("object")
        self.populate_block()

        self.block.generate_xml_node(root)

        image = root.find("image")
        self.assert_(image is None, "V4 Object Image blocks should not output anything to the combined object XML.")

    def test_BlockOIV4_load_header_from_xml(self):
        """ This test makes use of a special XML file."""
        path = os.path.join(os.getcwd(), "test", "blocks", "v4_OBHD.xml")
        self.block._load_header_from_xml(path)
        self.assertEqual(self.block.obj_id, 1001)

if __name__ == '__main__':
    unittest.main()

