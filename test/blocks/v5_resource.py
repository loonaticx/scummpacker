import xml.etree.ElementTree as et
import unittest
import os
from blocks.v5_resource import *

class BlockOBCDV5TestCase(unittest.TestCase):
    def setUp(self):
        self.block = BlockOBCDV5(4, 0x69)

    def populate_block(self):
        class MockCDHD(object):
            def generate_xml_node(self, parent_xml_node):
                pass
        self.block.cdhd = MockCDHD()
        self.block.cdhd.x = 1
        self.block.cdhd.y = 2
        self.block.cdhd.width = 3
        self.block.cdhd.height = 4
        self.block.cdhd.flags = 5
        self.block.cdhd.parent = 6
        self.block.cdhd.walk_x = 7
        self.block.cdhd.walk_y = 8
        self.block.cdhd.actor_dir = 9

    def test_BlockOBCDV5_generate_xml_node(self):
        root = et.Element("object")
        self.populate_block()

        self.block.generate_xml_node(root)

        code = root.find("code")
        self.assert_(code is None, "V5 Object Code blocks should not add a 'code' node to the combined object XML.")


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


class BlockOBIMV5TestCase(unittest.TestCase):
    def setUp(self):
        self.block = BlockOBIMV5(4, 0x69)

    def populate_block(self):
        class MockIMHD(object):
            def generate_xml_node(self, parent_xml_node):
                pass
        self.block.imhd = MockIMHD()
        self.block.imhd.x = 1
        self.block.imhd.y = 2
        self.block.imhd.width = 3
        self.block.imhd.height = 4
        self.block.imhd.flags = 5
        self.block.imhd.unknown = 6
        self.block.imhd.num_imnn = 7
        self.block.imhd.num_zpnn = 8

    def test_BlockOBIMV5_generate_xml_node(self):
        root = et.Element("object")
        self.populate_block()

        self.block.generate_xml_node(root)

        code = root.find("image")
        self.assert_(code is None, "V5 Object Image OBIM blocks should not add anything to the combined object XML.")


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

