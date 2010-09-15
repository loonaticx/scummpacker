import xml.etree.ElementTree as et
import unittest
import os
import cStringIO as StringIO

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
        """ Tests that the block generates expected values in output XML. """
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
        """ Tests that the block receives expected values from the XML.
        This test makes use of a special XML file."""
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

    def test_BlockOIV4_read_data(self):
        """ Tests that values are mapped from a packed resource file into
        the Block object."""
        script_data = "\x01\x02\x03\x04"
        resource = StringIO.StringIO(
            "\xE9\x03" + # object ID in LE order
            "\x01" + # unknown
            "\x02" + # x
            "\x83" + # y and parent state
            "\x04" + # width
            "\x05" + # parent
            "\x06\x00" + # walk_x
            "\x07\x00" + # walk_y
            "\x0A" + # height and actor_dir (height = 8, actor dir = 2)
            "\x0F" + # name offset
            "\x0E" + # verb table
            "TestObj\x00" + # object name
            script_data
        )

        decrypt = False
        self.block.size = 27
        def mock_read_raw_data(resource, size, descrypt):
            return resource.read(size)
        self.block._read_raw_data = mock_read_raw_data
        self.block._read_data(resource, 0, decrypt)
        self.assertEqual(self.block.obj_id, 1001)
        self.assertEqual(self.block.unknown, 1)
        self.assertEqual(self.block.x, 2)
        self.assertEqual(self.block.y, 3)
        self.assertEqual(self.block.parent_state, 0x80)
        self.assertEqual(self.block.width, 4)
        self.assertEqual(self.block.parent, 5)
        self.assertEqual(self.block.walk_x, 6)
        self.assertEqual(self.block.walk_y, 7)
        self.assertEqual(self.block.height, 8)
        self.assertEqual(self.block.actor_dir, 2)
        self.assertEqual(self.block.event_table, "\x0E")
        self.assertEqual(self.block.obj_name, "TestObj")
        self.assertEqual(self.block.script_data, script_data)

if __name__ == '__main__':
    unittest.main()
