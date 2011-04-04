import os
import re
import scummpacker_util as util
from blocks.common import AbstractBlock

class BlockOBIMShared(object):
    """ Shared by V5 and V6, slightly different header.
    Inheriting classes should also inherit from the appropriate container class,
    and need to define the imhd_class and container_class."""
    name = "OBIM"
    imhd_class = None
    container_class = None

    def _read_data(self, resource, start, decrypt, room_start=0):
        end = start + self.size

        # Load the header
        block = self.imhd_class(self.block_name_length, self.crypt_value)
        block.load_from_resource(resource)
        self.obj_id = block.obj_id # maybe should handle header info better
        self.imhd = block

        # Load the image data
        i = block.num_imnn
        while i > 0:
            block = self.container_class(self.block_name_length, self.crypt_value)
            block.load_from_resource(resource)
            self.append(block)
            i -= 1

    def load_from_file(self, path):
        # Load the header
        block = self.imhd_class(self.block_name_length, self.crypt_value)
        block.load_from_file(os.path.join(path, "OBHD.xml"))
        self.append(block)
        self.obj_id = block.obj_id
        self.imhd = block
        self.name = "OBIM"

        # Load the image data
        file_list = os.listdir(path)
        re_pattern = re.compile(r"IM[0-9a-fA-F]{2}")
        imnn_dirs = [f for f in file_list if re_pattern.match(f) != None]
        if len(imnn_dirs) != block.num_imnn:
            raise util.ScummPackerException("Number of images in the header ("
            + str(block.num_imnn)
            + ") does not match the number of image directories ("
            + str(len(imnn_dirs))
            + ")")

        for d in imnn_dirs:
            new_path = os.path.join(path, d)
            block = self.container_class(self.block_name_length, self.crypt_value)
            block.load_from_file(new_path)
            self.append(block)

    def generate_file_name(self):
        return ""

    def generate_xml_node(self, parent_node):
        """ Adds a new XML node to the given parent node."""
        self.imhd.generate_xml_node(parent_node)


class BlockOBCDShared(object):
    """ Shared by V5 and V6, slightly different header.
    Inheriting classes should also inherit from the appropriate container class,
    and need to define the cdhd_class, verb_class and obna_class."""
    name = "OBCD"
    cdhd_class = None
    verb_class = None
    obna_class = None

    def _read_data(self, resource, start, decrypt, room_start=0):
        end = start + self.size
        block = self.cdhd_class(self.block_name_length, self.crypt_value)
        block.load_from_resource(resource)
        self.obj_id = block.obj_id # maybe should handle header info better
        self.cdhd = block

        block = self.verb_class(self.block_name_length, self.crypt_value)
        block.load_from_resource(resource)
        self.verb = block

        block = self.obna_class(self.block_name_length, self.crypt_value)
        block.load_from_resource(resource)
        self.obna = block

        self.obj_name = self.obna.obj_name # cheat

    def load_from_file(self, path):
        self.name = "OBCD"
        block = self.cdhd_class(self.block_name_length, self.crypt_value)
        block.load_from_file(os.path.join(path, "OBHD.xml"))
        self.obj_id = block.obj_id # maybe should handle header info better
        self.cdhd = block

        block = self.verb_class(self.block_name_length, self.crypt_value)
        block.load_from_file(os.path.join(path, "VERB.dmp")) # hmm
        self.verb = block

        block = self.obna_class(self.block_name_length, self.crypt_value)
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


class BlockDefaultSharedV5V6(AbstractBlock):
    def _read_header(self, resource, decrypt):
        # Should be reversed for old format resources
        self.name = self._read_name(resource, decrypt)
        self.size = self._read_size(resource, decrypt)

    def _write_header(self, outfile, encrypt):
        name = util.crypt(self.name, self.crypt_value) if encrypt else self.name
        outfile.write(name)
        size = util.int2str(self.size, is_BE=util.BE, crypt_val=(self.crypt_value if encrypt else None))
        outfile.write(size)

    def _write_dummy_header(self, outfile, encrypt):
        """Writes placeholder information (block name, block size of 0)"""
        name = util.crypt(self.name, self.crypt_value) if encrypt else self.name
        outfile.write(name)
        size = util.int2str(0, is_BE=util.BE, crypt_val=(self.crypt_value if encrypt else None))
        outfile.write(size)