#! /usr/bin/python
import array
import logging
import os
import xml.etree.ElementTree as et
import scummpacker_control as control
import scummpacker_util as util

class AbstractBlock(object):
    def __init__(self, block_name_length, crypt_value, *args, **kwds):
        super(AbstractBlock, self).__init__(*args, **kwds)
        self.block_name_length = block_name_length
        self.crypt_value = crypt_value

    def load_from_resource(self, resource, room_start=0):
        start = resource.tell()
        logging.debug("Loading block from resource: " + str(start))
        self._read_header(resource, True)
        self._read_data(resource, start, True)

    def save_to_resource(self, resource, room_start=0):
        #start = resource.tell()
        self._write_header(resource, True)
        self._write_data(resource, True)

    def _read_header(self, resource, decrypt):
        # Different in old format resources
        raise NotImplementedError("This method must be overriden by a concrete class.")

    def _read_data(self, resource, start, decrypt):
        data = self._read_raw_data(resource, self.size - (resource.tell() - start), decrypt)
        self.data = data

    def _read_name(self, resource, decrypt):
        name = resource.read(self.block_name_length)
        if decrypt:
            name = util.crypt(name, self.crypt_value)
        logging.debug("Block name: " + str(name))
        return name

    def _read_size(self, resource, decrypt):
        size = resource.read(4)
        if decrypt:
            size = util.crypt(size, self.crypt_value)
        return util.str_to_int(size, is_BE=util.BE)

    def _read_raw_data(self, resource, size, decrypt):
        data = array.array('B')
        data.fromfile(resource, size)
        if decrypt:
            data = util.crypt(data, self.crypt_value)
        return data

    def load_from_file(self, path):
        block_file = file(path, 'rb')
        start = block_file.tell()
        self._read_header(block_file, False)
        self._read_data(block_file, start, False)
        block_file.close()

    def save_to_file(self, path):
        outfile = file(os.path.join(path, self.generate_file_name()), 'wb')
        self._write_header(outfile, False)
        self._write_data(outfile, False)
        outfile.close()

    def _write_header(self, outfile, encrypt):
        # Different in old format resources
        raise NotImplementedError("This method must be overriden by a concrete class.")

    def _write_dummy_header(self, outfile, encrypt):
        """Writes placeholder information (block name, block size of 0)"""
        raise NotImplementedError("This method must be overriden by a concrete class.")

    def _write_data(self, outfile, encrypt):
        self._write_raw_data(outfile, encrypt)

    def _write_raw_data(self, outfile, encrypt):
        data = self.data
        if encrypt:
            data = util.crypt(data, self.crypt_value)
        data.tofile(outfile)

    def generate_file_name(self):
        return self.name + ".dmp"

    def __repr__(self):
        return "[" + self.name + "]"

class BlockContainer(AbstractBlock):
    block_ordering = [
        # To be overridden in version-specific deriving classes.
    ]

    def __init__(self, *args, **kwds):
        super(BlockContainer, self).__init__(*args, **kwds)
        self.children = []
        self.order_map = {}

    def _read_data(self, resource, start, decrypt):
        logging.debug("Reading children from container block...")
        end = start + self.size
        while resource.tell() < end:
            block = control.block_dispatcher.dispatch_next_block(resource)
            block.load_from_resource(resource, start)
            self.append(block)

    def _find_block_rank_lookup_name(self, block):
        rank_lookup_name = block.name
        # dumb crap here but I'm sick of working on this crappy piece of software
        if rank_lookup_name[:2] == "ZP" or rank_lookup_name[:2] == "IM":
            rank_lookup_name = rank_lookup_name[:2]
        return rank_lookup_name

    def _find_block_rank(self, block):
        rank_lookup_name = self._find_block_rank_lookup_name(block)
        block_rank = self.block_ordering.index(rank_lookup_name) # requires all block types are listed
        return block_rank

    def append(self, block):
        """Maintains sorted order for children."""
        rank_lookup_name = self._find_block_rank_lookup_name(block)
        block_rank = self._find_block_rank(block)
        #logging.debug("Appending block: " + str(block.name))

        for i, c in enumerate(self.children):
            c_rank = self._find_block_rank(c)
            # Same block type, so look for a specified order for this block type.
            if c_rank == block_rank:
                if not rank_lookup_name in self.order_map:
                    continue # no order specified, continue iteration, appending after all existing blocks of this type
                order_list = self.order_map[rank_lookup_name]
                if not block.index in order_list:
                    continue # if the order of the added block is not known, append after existing blocks
                if not c.index in order_list:
                    self.children.insert(i, block)
                    return # if existing block has no order but new block done, insert new block before unordered block.
                block_order = order_list.index(block.index)
                c_order = order_list.index(c.index)
                if c_order > block_order:
                    self.children.insert(i, block)
                    return # existing block comes after block being added
            elif c_rank > block_rank:
                #logging.debug("rank_lookup_name: " + str(block.name) + ", c_rank: " + str(c_rank) + ", block_rank: " + str(block_rank))
                self.children.insert(i, block)
                return
        #logging.debug("appending block, rank_lookup_name: " + str(block.name) + ", block_rank: " + str(block_rank))
        self.children.append(block)

    def save_to_file(self, path):
        newpath = self._create_directory(path)
        self._save_children(newpath)
        self._save_order_to_xml(newpath)

    def _create_directory(self, start_path):
        newpath = os.path.join(start_path, self.generate_file_name())
        if not os.path.isdir(newpath):
            os.mkdir(newpath) # throws an exception if can't create dir
        return newpath

    def _save_children(self, path):
        for child in self.children:
            child.save_to_file(path)

    def _save_order_to_xml(self, path):
        root = et.Element("order")

        curr_type = None
        ol_node = None
        for c in self.children:
            if not hasattr(c, "index"):
                continue
            block_type = self._find_block_rank_lookup_name(c)
            # if block type is new, create new list
            if block_type != curr_type:
                ol_node = et.SubElement(root, "order-list")
                ol_node.set("block-type", block_type)
                curr_type = block_type
            et.SubElement(ol_node, "order-entry").text = util.output_int_to_xml(c.index)

        if len(root.getchildren()) == 0:
            return

        util.indent_elementtree(root)
        et.ElementTree(root).write(os.path.join(path, "order.xml"))

    def load_from_file(self, path):
        self.name = os.path.split(path)[1]
        self.children = []
        self.order_map = {}

        file_list = os.listdir(path)
        if "order.xml" in file_list:
            file_list.remove("order.xml")
            self._load_order_from_xml(os.path.join(path, "order.xml"))

        for f in file_list:
            b = control.file_dispatcher.dispatch_next_block(f)
            if b != None:
                b.load_from_file(os.path.join(path, f))
                self.append(b)

    def _load_order_from_xml(self, path):
        if not os.path.isfile(path):
            # If order.xml does not exist, use whatever order we want.
            # Should not get here...
            return

        tree = et.parse(path)
        root = tree.getroot()

        order_map = {}

        for ol in root.findall("order-list"):
            block_type = ol.get("block-type")
            order_list = []
            for o in ol.findall("order-entry"):
                order_list.append(util.parse_int_from_xml(o.text))
            order_map[block_type] = order_list

        #logging.debug(str(order_map))
        self.order_map = order_map

    def save_to_resource(self, resource, room_start=0):
        start = resource.tell()

        # write dummy header
        self._write_dummy_header(resource, True)
        # process children
        for c in self.children:
            c.save_to_resource(resource, room_start)

        # go back and write size of block
        end = resource.tell()
        self.size = end - start
        resource.flush()
        resource.seek(start, os.SEEK_SET)
        self._write_header(resource, True)
        resource.seek(end, os.SEEK_SET)

    def generate_file_name(self):
        return self.name

    def __repr__(self):
        childstr = [str(c) for c in self.children]
        return "[" + self.name + ", " + ", ".join(childstr) + "]"