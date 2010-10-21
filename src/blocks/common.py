#! /usr/bin/python
import array
from collections import defaultdict
import logging
import os
import re
import struct
import xml.etree.ElementTree as et
import scummpacker_control as control
import scummpacker_util as util

class AbstractBlock(object):
    xml_structure = tuple() # placeholder
    
    def __init__(self, block_name_length, crypt_value, *args, **kwds):
        super(AbstractBlock, self).__init__(*args, **kwds)
        self.block_name_length = block_name_length
        self.crypt_value = crypt_value

    def load_from_resource(self, resource, room_start=0):
        start = resource.tell()
        self._read_header(resource, True)
        #logging.debug("%s loading from room start %s" % (self.name, room_start))
        self._read_data(resource, start, True, room_start)

    def save_to_resource(self, resource, room_start=0):
        self._write_header(resource, True)
        self._write_data(resource, True)

    def _read_header(self, resource, decrypt):
        # Different in old format resources
        raise NotImplementedError("This method must be overriden by a concrete class.")

    def _read_data(self, resource, start, decrypt, room_start=0):
        data = self._read_raw_data(resource, self.size - (resource.tell() - start), decrypt)
        self.data = data

    def _read_name(self, resource, decrypt):
        name = resource.read(self.block_name_length)
        if decrypt:
            name = util.crypt(name, self.crypt_value)
        return name

    def _read_size(self, resource, decrypt):
        size = resource.read(4)
        if decrypt:
            size = util.crypt(size, self.crypt_value)
        return util.str2int(size, is_BE=util.BE)

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
        self._write_raw_data(outfile, self.data, encrypt)

    def _write_raw_data(self, outfile, data, encrypt):
        data_out = data
        if encrypt:
            data_out = util.crypt(data_out, self.crypt_value)
        data_out.tofile(outfile)

    def generate_file_name(self):
        return self.name + ".dmp"

    def __repr__(self):
        return "[" + self.name + "]"

    def generate_xml_node(self, parent_node):
        """ Adds a new XML node to the given parent node.

        Not used by every block. To use it, the "xml_structure" property
        should be populated, and this method must be specifically called,
        either from a containing block, or from the "save_to_file" method."""
        util.xml_helper.write(self, parent_node, self.xml_structure)

    def read_xml_node(self, parent_node):
        """ Reads data from the given root node.

        Not used by every block. To use it, the "xml_structure" property
        should be populated, and this method must be specifically called,
        either from a containing block, or from the "save_to_resource" method."""
        util.xml_helper.read(self, parent_node, self.xml_structure)

class BlockContainer(AbstractBlock):
    block_ordering = [
        # To be overridden in version-specific deriving classes.
    ]

    def __init__(self, *args, **kwds):
        super(BlockContainer, self).__init__(*args, **kwds)
        self.children = []
        self.order_map = {}

    def _read_data(self, resource, start, decrypt, room_start=0):
        end = start + self.size
        while resource.tell() < end:
            block = control.block_dispatcher.dispatch_next_block(resource)
            block.load_from_resource(resource, room_start)
            self.append(block)

    def _find_block_rank_lookup_name(self, block):
        rank_lookup_name = block.name
        # dumb crap here but I'm sick of working on this crappy piece of software
        if rank_lookup_name[:2] == "ZP" or rank_lookup_name[:2] == "IM":
            rank_lookup_name = rank_lookup_name[:2]
        if rank_lookup_name == "\x00\x00":
            rank_lookup_name = "00"
        return rank_lookup_name

    def _find_block_rank(self, block):
        rank_lookup_name = self._find_block_rank_lookup_name(block)
        block_rank = self.block_ordering.index(rank_lookup_name) # requires all block types are listed
        return block_rank

    def append(self, block):
        """Maintains sorted order for children."""
        rank_lookup_name = self._find_block_rank_lookup_name(block)
        block_rank = self._find_block_rank(block)

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
                self.children.insert(i, block)
                return
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
            if not hasattr(c, "index") or c.index is None:
                continue
            block_type = self._find_block_rank_lookup_name(c)
            # if block type is new, create new list
            if block_type != curr_type:
                ol_node = et.SubElement(root, "order-list")
                ol_node.set("block-type", block_type)
                curr_type = block_type
            et.SubElement(ol_node, "order-entry").text = util.int2xml(c.index)

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
                order_list.append(util.xml2int(o.text))
            order_map[block_type] = order_list

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


class BlockGloballyIndexed(AbstractBlock):
    lf_name = None # override in concrete class
    room_offset_name = None # override in concrete class
    #lookup_name = override in concrete class if necessary, via property method

    def __init__(self, *args, **kwds):
        super(BlockGloballyIndexed, self).__init__(*args, **kwds)
        self.index = None
        self.is_unknown = False

    def load_from_resource(self, resource, room_start=0):
        location = resource.tell()
        super(BlockGloballyIndexed, self).load_from_resource(resource, room_start)
        try:
            self._lookup_index(location, room_start)
        except util.ScummPackerUnrecognisedIndexException, suie:
            self._handle_unknown_index(location, room_start)

    def _lookup_index(self, location, room_start):
        room_num = control.global_index_map.get_index(self.lf_name, (control.disk_spanning_counter, room_start))
        room_offset = control.global_index_map.get_index(self.room_offset_name, room_num)
        self.index = control.global_index_map.get_index(self.lookup_name,
                                                         (room_num, location - room_offset))

    def _handle_unknown_index(self, location, room_start):
        room_num = control.global_index_map.get_index(self.lf_name, (control.disk_spanning_counter, room_start))
        logging.debug("Unknown block at room num: %s" % room_num)
        room_offset = control.global_index_map.get_index(self.room_offset_name, room_num)
        logging.debug("Unknown block at room offset: %s" % str(location - room_offset))
        logging.error(("Block \"%s\" at offset %s has no entry in the index file (.000). " +
                      "It can not be re-packed or used in the game.") % (self.name, location))
        self.is_unknown = True
        self.index = control.unknown_blocks_counter.get_next_index(self.lookup_name)

    def save_to_resource(self, resource, room_start=0):
        # Look up the start of the current ROOM block, store
        # a mapping of this block's index and room #/offset.
        # Later on, our directories will just treat global_index_map as a list of
        # tables and go through all of the values.
        location = resource.tell()
        self._map_index(location, room_start)
        super(BlockGloballyIndexed, self).save_to_resource(resource, room_start)

    def _map_index(self, location, room_start):
        room_num = control.global_index_map.get_index(self.lf_name, (control.disk_spanning_counter, room_start))
        room_offset = control.global_index_map.get_index(self.room_offset_name, room_num)
        control.global_index_map.map_index(self.lookup_name,
                                           (room_num, location - room_offset),
                                           self.index)

    def load_from_file(self, path):
        """ Assumes we won't get any 'unknown' blocks, based on the regex in the file walker."""
        if os.path.isdir(path):
            index = os.path.split(path)[1][-3:]
        else:
            fname = os.path.split(path)[1]
            index = os.path.splitext(fname)[0][-3:]
        try:
            self.index = int(index)
        except ValueError, ve:
            raise util.ScummPackerException(str(self.index) + " is an invalid index for resource " + path)
        super(BlockGloballyIndexed, self).load_from_file(path)

    def generate_file_name(self):
        return (self.name
                + "_"
                + ("unk_" if self.is_unknown else "")
                + str(self.index).zfill(3) + ".dmp")

    def __repr__(self):
        return "[" + self.name + ":" + ("unk_" if self.is_unknown else "") + str(self.index).zfill(3) + "]"

    @property
    def lookup_name(self):
        """ This method returns the name to be used when looking up/storing values in the global index map.
        
        This allows inheriting classes to specify a lookup name different to the block name."""
        return self.name

    
class BlockLocalScript(AbstractBlock):
    name = None # override in concrete class

    def _read_data(self, resource, start, decrypt, room_start=0):
        script_id = resource.read(1)
        if decrypt:
            script_id = util.crypt(script_id, self.crypt_value)
        self.script_id = util.str2int(script_id)
        self.data = self._read_raw_data(resource, self.size - (resource.tell() - start), decrypt)

    def _write_data(self, outfile, encrypt):
        script_num = util.int2str(self.script_id, num_bytes=1)
        if encrypt:
            script_num = util.crypt(script_num, self.crypt_value)
        outfile.write(script_num)
        self._write_raw_data(outfile, self.data, encrypt)

    def generate_file_name(self):
        return self.name + "_" + str(self.script_id).zfill(3) + ".dmp"

class BlockLucasartsEntertainmentContainer(BlockContainer):
    def __init__(self, *args, **kwds):
        super(BlockLucasartsEntertainmentContainer, self).__init__(*args, **kwds)
        self._init_class_data()

    def _init_class_data(self):
        self.name = NotImplementedError("This property must be overridden by inheriting classes.")
        self.OFFSET_CLASS = NotImplementedError("This property must be overridden by inheriting classes.")
    
    def load_from_file(self, path):
        # assume input path is actually the directory containing the LECF dir
        super(BlockLucasartsEntertainmentContainer, self).load_from_file(os.path.join(path, self.name))

    def save_to_resource(self, resource, room_start=0):
        start = resource.tell()

        # write dummy header
        self._write_dummy_header(resource, True)

        # write dummy LOFF
        loff_start = resource.tell()
        loff_block = self.OFFSET_CLASS(self.block_name_length, self.crypt_value)
        num_rooms = len(self.children)
        loff_block.write_dummy_block(resource, num_rooms)

        # process children
        for c in self.children:
            c.save_to_resource(resource, room_start)

        # go back and write size of LECF block (i.e. the whole ".001" file)
        self.size = resource.tell() - start
        resource.flush()
        end = resource.tell()
        resource.seek(start, os.SEEK_SET)
        self._write_header(resource, True)

        # go back and write the LOFF block
        loff_block.save_to_resource(resource, room_start)
        resource.seek(end, os.SEEK_SET)

    def __repr__(self):
        childstr = [str(c) for c in self.children]
        return "[" + self.name + ", " + ", \n".join(childstr) + "]"
    
class BlockLucasartsFile(BlockContainer, BlockGloballyIndexed):
    """ Anything inheriting from this class should also inherit from the concrete versions
    of BlockContainer and BlockGloballyIndexed."""
    is_unknown = False
    disk_lookup_name = NotImplementedError("This property must be overridden by inheriting classes.")

    def load_from_resource(self, resource, room_start=0):
        location = resource.tell()
        self._read_header(resource, True)
        self._read_data(resource, location, True, location)
        try:
            self.index = control.global_index_map.get_index(self.name, location)
        except util.ScummPackerUnrecognisedIndexException, suie:
            logging.error(("Block \"%s\" at offset %s has no entry in the index file (.000). " + 
                          "It can not be re-packed or used in the game.") % (self.name, location))
            self.is_unknown = True
            self.index = control.unknown_blocks_counter.get_next_index(self.name)

    def save_to_resource(self, resource, room_start=0):
        location = resource.tell()
        room_start = location
        # Map the location of the LF block.
        control.global_index_map.map_index(self.name, location, self.index)
        # Map the room number to the disk number, for later use in
        # 0R/DROO blocks in the index file.
        control.global_index_map.map_index(self.disk_lookup_name,
                                           self.index,
                                           control.disk_spanning_counter)
        super(BlockLucasartsFile, self).save_to_resource(resource, room_start)

    def save_to_file(self, path):
        logging.info("Saving block %s" % self.generate_file_name())
        super(BlockLucasartsFile, self).save_to_file(path)

    def load_from_file(self, path):
        name = os.path.split(path)[1]
        self.name = name.split('_')[0]
        self.index = int(name.split('_')[1])
        self.children = []

        file_list = os.listdir(path)
        if "order.xml" in file_list:
            file_list.remove("order.xml")
            self._load_order_from_xml(os.path.join(path, "order.xml"))

        for f in file_list:
            b = control.file_dispatcher.dispatch_next_block(f)
            if b != None:
                b.load_from_file(os.path.join(path, f))
                self.append(b)

    def generate_file_name(self):
        return (self.name
                + "_"
                + ("unk_" if self.is_unknown else "")
                + str(self.index).zfill(3))

    def __repr__(self):
        childstr = [str(c) for c in self.children]
        return ("["
                + self.name
                + ":"
                + ("unk_" if self.is_unknown else "")
                + str(self.index).zfill(3)
                + ", "
                + ", ".join(childstr)
                + "]")

class BlockRoomOffsets(AbstractBlock):
    name = NotImplementedError("This property must be overridden by inheriting classes.") # string
    LFLF_NAME = NotImplementedError("This property must be overridden by inheriting classes.") # class name (string)
    ROOM_OFFSET_NAME = NotImplementedError("This property must be overridden by inheriting classes.") # class name (string)
    OFFSET_POINTS_TO_ROOM = NotImplementedError("This property must be overridden by inheriting classes.") # boolean
    disk_lookup_name = NotImplementedError("This property must be overridden by inheriting classes.") # string

    def _read_data(self, resource, start, decrypt, room_start=0):
        num_rooms = util.str2int(resource.read(1),
                                    crypt_val=(self.crypt_value if decrypt else None))

        for _ in xrange(num_rooms):
            room_no = util.str2int(resource.read(1),
                                      crypt_val=(self.crypt_value if decrypt else None))
            if self.OFFSET_POINTS_TO_ROOM:
                room_offset = util.str2int(resource.read(4),
                                              crypt_val=(self.crypt_value if decrypt else None))
                lf_offset = room_offset - self.block_name_length - 4
            else:
                lf_offset = util.str2int(resource.read(4),
                                            crypt_val=(self.crypt_value if decrypt else None))
                room_offset = lf_offset + 2 + self.block_name_length + 4 # add 2 bytes for the room number/index of LF block. 
            control.global_index_map.map_index(self.LFLF_NAME, (control.disk_spanning_counter, lf_offset), room_no)
            control.global_index_map.map_index(self.ROOM_OFFSET_NAME, room_no, room_offset) # HACK

    def save_to_file(self, path):
        """Don't need to save offsets since they're calculated when packing."""
        return

    def save_to_resource(self, resource, room_start=0):
        """This method should only be called after write_dummy_block has been invoked,
        otherwise this block may have no size attribute initialised."""
        # Write name/size (probably again, since write_dummy_block also writes it)
        self._write_header(resource, True)
        # Write number of rooms, followed by offset table
        # Possible inconsistency, in that this uses the global index map for ROOM blocks,
        #  whereas the "write_dummy_block" just looks at the number passed in, which
        #  comes from the number of entries in the file system.
        if self.OFFSET_POINTS_TO_ROOM:
            room_table = []
            for room_item in \
            sorted(control.global_index_map.items(self.ROOM_OFFSET_NAME)):
                # Don't write rooms not on this disk
                room_num = room_item[0]
                room_disk = control.global_index_map.get_index(self.disk_lookup_name, room_num)
                if room_disk == control.disk_spanning_counter:
                    room_table.append(room_item)

            num_of_rooms = len(room_table)
            resource.write(util.int2str(num_of_rooms, 1, crypt_val=self.crypt_value))
            for room_num, room_offset in room_table:
                room_num = int(room_num)
                resource.write(util.int2str(room_num, 1, crypt_val=self.crypt_value))
                resource.write(util.int2str(room_offset, 4, util.LE, self.crypt_value))
        else:
            room_table = []
            for lflf_item in \
            sorted(control.global_index_map.items(self.LFLF_NAME)):
                # Don't write rooms not on this disk
                room_num = lflf_item[1]
                room_disk = control.global_index_map.get_index(self.disk_lookup_name, room_num)
                if room_disk == control.disk_spanning_counter:
                    room_table.append(lflf_item)

            num_of_rooms = len(room_table)
            resource.write(util.int2str(num_of_rooms, 1, crypt_val=self.crypt_value))
            for lf_offset, room_num in room_table:
                room_num = int(room_num)
                resource.write(util.int2str(room_num, 1, crypt_val=self.crypt_value))
                resource.write(util.int2str(lf_offset, 4, util.LE, self.crypt_value))

    def write_dummy_block(self, resource, num_rooms):
        """This method should be called before save_to_resource. It just
        reserves space until the real block is written.

        The reason for doing this is that the block begins at the start of the
        resource file, but contains the offsets of all of the room blocks, which
        won't be known until after they've all been written."""
        block_start = resource.tell()
        self._write_dummy_header(resource, True)
        resource.write(util.int2str(num_rooms, 1, crypt_val=self.crypt_value))
        for _ in xrange(num_rooms):
            resource.write(util.int2str(0, 1, crypt_val=self.crypt_value) * 5)
        block_end = resource.tell()
        self.size = block_end - block_start
    
class BlockRoom(BlockContainer): # also globally indexed

    def __init__(self, *args, **kwds):
        super(BlockRoom, self).__init__(*args, **kwds)
        self._init_class_data()

    def _init_class_data(self):
        self.name = None
        self.lf_name = None
        self.room_offset_name = None
        self.script_types = frozenset()
        self.object_types = frozenset()
        self.object_between_types = frozenset() # workaround for V4 "NL" and "SL"
        self.object_image_type = None
        self.object_code_type = None
        self.num_scripts_type = None
        self.script_container_class = ScriptBlockContainer
        self.object_container_class = ObjectBlockContainer
        self.dodgy_offsets = {} # workaround for junk room data in MI1EGA/MI1VGA
        raise NotImplementedError("This method must be overriden by a concrete class.")

    def _read_data(self, resource, start, decrypt, room_start=0):
        end = start + self.size
        object_container = self.object_container_class(self.block_name_length, self.crypt_value)
        script_container = self.script_container_class(self.block_name_length, self.crypt_value)
        while resource.tell() < end:
            if control.global_args.game in self.dodgy_offsets:
                doff_set = self.dodgy_offsets[control.global_args.game]
                if resource.tell() - 4 - self.block_name_length in doff_set:
                    logging.warning("Skipping known dodgy room data at offset %s" % resource.tell())
                    resource.seek(end)
                    break
            block = control.block_dispatcher.dispatch_next_block(resource)
            block.load_from_resource(resource, room_start)
            if block.name in self.script_types:
                script_container.append(block)
            elif block.name == self.object_image_type:
                object_container.add_image_block(block)
            elif block.name == self.object_code_type:
                object_container.add_code_block(block)
            elif block.name in self.object_between_types:
                object_container.add_between_block(block)
            elif block.name == self.num_scripts_type: # ignore this since we can generate it
                del block
                continue
            else:
                self.append(block)
        self.append(object_container)
        self.append(script_container)

    def save_to_resource(self, resource, room_start=0):
        location = resource.tell()
        room_num = control.global_index_map.get_index(self.lf_name, (control.disk_spanning_counter, room_start))
        logging.debug("Saving room: %s" % room_num)
        control.global_index_map.map_index(self.room_offset_name, room_num, location)
        super(BlockRoom, self).save_to_resource(resource, room_start)


class BlockIndexDirectory(AbstractBlock):
    """ Generic index directory """
    DIR_TYPES = NotImplementedError("This property must be overridden by inheriting classes.")
    MIN_ENTRIES = NotImplementedError("This property must be overridden by inheriting classes.")

    def _read_data(self, resource, start, decrypt, room_start=0):
        raise NotImplementedError("This method must be overridden by inheriting classes.")

    def save_to_file(self, path):
        """This block is generated when saving to a resource."""
        return

    def save_to_resource(self, resource, room_start=0):
        # is room_start required? nah, just there for interface compliance.
        #for i, key in enumerate()
        items = control.global_index_map.items(self.DIR_TYPES[self.name])
        item_map = {}
        if len(items) == 0:
            logging.info("No indexes found for block type \"" + self.name + "\" - are there any files of this block type?")
            num_items = self.MIN_ENTRIES[control.global_args.game][self.name]
        else:
            items.sort(cmp=lambda x, y: cmp(x[1], y[1])) # sort by resource number
            # Need to pad items out, so take last entry's number as the number of items
            num_items = items[-1][1]
            if self.name in self.MIN_ENTRIES[control.global_args.game] and \
               num_items < self.MIN_ENTRIES[control.global_args.game][self.name]:
                num_items = self.MIN_ENTRIES[control.global_args.game][self.name]
            # Create map with reversed key/value pairs
            for i, j in items:
                item_map[j] = i

        # Bleeech
        self.size = 5 * num_items + 2 + self.block_name_length + 4
        self._write_header(resource, True)

        resource.write(util.int2str(num_items, 2, crypt_val=self.crypt_value))
        self._save_table_data(resource, num_items, item_map)

    def _save_table_data(self, resource, num_items, item_map):
        for i in xrange(num_items):
            if not i in item_map:
                # write dummy values for unused item numbers.
                resource.write(util.int2str(0, 1, crypt_val=self.crypt_value))
            else:
                room_num, _ = item_map[i]
                resource.write(util.int2str(room_num, 1, crypt_val=self.crypt_value))
        for i in xrange(num_items):
            if not i in item_map:
                # write dummy values for unused item numbers.
                resource.write(util.int2str(0, 4, crypt_val=self.crypt_value))
            else:
                _, offset = item_map[i]
                resource.write(util.int2str(offset, 4, crypt_val=self.crypt_value))

class BlockObjectIndexes(AbstractBlock):
    name = NotImplementedError("This property must be overridden by inheriting classes.")
    class_data_size = NotImplementedError("This property must be overridden by inheriting classes.")

    def _read_data(self, resource, start, decrypt, room_start=0):
        num_items = util.str2int(resource.read(2), crypt_val=(self.crypt_value if decrypt else None))
        self.objects = []
        # Read all owner+state values
        for _ in xrange(num_items):
            owner_and_state = util.str2int(resource.read(1), crypt_val=(self.crypt_value if decrypt else None))
            owner = (owner_and_state & 0xF0) >> 4
            state = owner_and_state & 0x0F
            self.objects.append([owner, state])
        # Read all class data values
        for i in xrange(num_items):
            class_data = util.str2int(resource.read(self.class_data_size), crypt_val=(self.crypt_value if decrypt else None))
            self.objects[i].append(class_data)

    def load_from_file(self, path):
        tree = et.parse(path)

        self.objects = []
        for obj_node in tree.getiterator("object-entry"):
            obj_id = int(obj_node.find("id").text)
            if obj_id != obj_id == len(self.objects) + 1:
                raise util.ScummPackerException("Entries in object ID XML must be in sorted order with no gaps in ID numbering.")
            owner = util.xml2int(obj_node.find("owner").text)
            state = util.xml2int(obj_node.find("state").text)
            class_data = util.xml2int(obj_node.find("class-data").text)
            self.objects.append([owner, state, class_data])

    def save_to_file(self, path):
        root = et.Element("object-directory")

        for i in xrange(len(self.objects)):
            owner, state, class_data = self.objects[i]
            obj_node = et.SubElement(root, "object-entry")
            et.SubElement(obj_node, "id").text = util.int2xml(i + 1)
            et.SubElement(obj_node, "owner").text = util.int2xml(owner)
            et.SubElement(obj_node, "state").text = util.int2xml(state)
            et.SubElement(obj_node, "class-data").text = util.hex2xml(class_data)

        util.indent_elementtree(root)
        et.ElementTree(root).write(os.path.join(path, "dobj.xml"))

    def save_to_resource(self, resource, room_start=0):
        """ TODO: allow filling of unspecified values (e.g. if entries for
        86 and 88 exist but not 87, create a dummy entry for 87."""
        num_items = len(self.objects)

        entry_size = 1 + self.class_data_size
        self.size = entry_size * num_items + 2 + self.block_name_length + 4
        self._write_header(resource, True)

        resource.write(util.int2str(num_items, 2, crypt_val=self.crypt_value))
        self._save_table_data(resource)

    def _save_table_data(self, resource):
        for owner, state, _ in self.objects:
            combined_val = ((owner & 0x0F) << 4) | (state & 0x0F)
            resource.write(util.int2str(combined_val, 1, crypt_val=self.crypt_value))
        for _, _, class_data in self.objects:
            resource.write(util.int2str(class_data, self.class_data_size, crypt_val=self.crypt_value))
                
class BlockRoomIndexes(AbstractBlock):
    """Directory of offsets to ROOM blocks. Also maps disk spanning.
    
    Don't really seem to be used much for V5 and LOOM CD. It is used in Monkey Island EGA/VGA.

    Each game seems to have a different padding length."""
    name = NotImplementedError("This property must be overridden by inheriting classes.")
    DEFAULT_PADDING_LENGTHS = NotImplementedError("This property must be overridden by inheriting classes.")
    default_disk_or_room_number = 0
    default_offset = 0

    def __init__(self, *args, **kwds):
        # Store a mapping of disk numbers to room numbers.
        self.disk_spanning = defaultdict(list)
        self.padding_length = kwds.get('padding_length',
                                       self.DEFAULT_PADDING_LENGTHS[control.global_args.game])
        super(BlockRoomIndexes, self).__init__(*args, **kwds)

    def _read_data(self, resource, start, decrypt, room_start=0):
        raise NotImplementedError("This method must be overridden by inheriting classes.")       
        
    def save_to_file(self, path):
        """This block is generated when saving to a resource."""
        pass
        
    def save_to_resource(self, resource, room_start=0):
        raise NotImplementedError("This method must be overridden by inheriting classes.")

class BlockRoomHeader(AbstractBlock):
    name = NotImplementedError("This property must be overridden by inheriting classes.")
    xml_structure = (
        ("width", 'i', 'width'),
        ("height", 'i', 'height'),
        ("num_objects", 'i', 'num_objects')
    )

    def _read_data(self, resource, start, decrypt, room_start=0):
        """
        width 16le
        height 16le
        num_objects 16le
        """
        data = resource.read(6)
        if decrypt:
            data = util.crypt(data, self.crypt_value)
        values = struct.unpack("<3H", data)
        del data

        # Unpack the values
        self.width, self.height, self.num_objects = values
        del values

    def load_from_file(self, path):
        self.size = 6 + self.block_name_length + 4
        self._load_header_from_xml(path)

    def _load_header_from_xml(self, path):
        tree = et.parse(path)
        root = tree.getroot()

        self.read_xml_node(root)

    def save_to_file(self, path):
        root = et.Element("room")

        self.generate_xml_node(root)

        util.indent_elementtree(root)
        et.ElementTree(root).write(os.path.join(path, self.name + ".xml"))

    def _write_data(self, outfile, encrypt):
        """ Assumes it's writing to a resource."""
        data = struct.pack("<3H", self.width, self.height, self.num_objects)
        if encrypt:
            data = util.crypt(data, self.crypt_value)
        outfile.write(data)


class BlockRoomNames(AbstractBlock):
    name_length = 9
    name = NotImplementedError("This property must be overridden by inheriting classes.")

    def _read_data(self, resource, start, decrypt, room_start=0):
        end = start + self.size
        self.room_names = []
        while resource.tell() < end:
            room_no = util.str2int(resource.read(1), crypt_val=(self.crypt_value if decrypt else None))
            if room_no == 0: # end of list marked by 0x00
                break
            room_name = resource.read(self.name_length)
            if decrypt:
                room_name = util.crypt(room_name, self.crypt_value)
            room_name = util.crypt(room_name, 0xFF).rstrip("\x00")
            self.room_names.append((room_no, room_name))
            control.global_index_map.map_index(self.name, room_no, room_name)

    def save_to_file(self, path):
        root = et.Element("room_names")

        for room_no, room_name in self.room_names:
            room = et.SubElement(root, "room")
            et.SubElement(room, "id").text = util.int2xml(room_no)
            et.SubElement(room, "name").text = util.escape_invalid_chars(room_name)

        util.indent_elementtree(root)
        et.ElementTree(root).write(os.path.join(path, "roomnames.xml"))

    def load_from_file(self, path):
        tree = et.parse(path)
        root = tree.getroot()

        self.room_names = []
        for room in root.findall("room"):
            room_no = util.xml2int(room.find("id").text)
            room_name = room.find("name").text
            if room_name == None:
                room_name = ''
            room_name = util.unescape_invalid_chars(room_name)
            self.room_names.append((room_no, room_name))
            control.global_index_map.map_index(self.name, room_no, room_name)

    def save_to_resource(self, resource, room_start=0):
        self.size = 10 * len(self.room_names) + 1 + self.block_name_length + 4
        self._write_header(resource, True)
        for room_no, room_name in self.room_names:
            resource.write(util.int2str(room_no, 1, crypt_val=self.crypt_value))
            # pad/truncate room name to 8 characters
            room_name = (room_name + ("\x00" * (self.name_length - len(room_name)))
                if len(room_name) < self.name_length
                else room_name[:self.name_length])
            resource.write(util.crypt(room_name, self.crypt_value ^ 0xFF if self.crypt_value else 0xFF))
        resource.write(util.int2str(0, 1, crypt_val=self.crypt_value))        
                
class ObjectBlockContainer(object):
    """ Contains objects, which contain image and code blocks."""

    def __init__(self, block_name_length, crypt_value, *args, **kwds):
        self._init_class_data()
        self.objects = {}
        self.obj_id_name_length = 4 # should be increased depending on number of objects in the game
        self.block_name_length = block_name_length
        self.crypt_value = crypt_value
        self.name = "objects"
        self.order_map = { self.obcd_name : [], self.obim_name : [] }
        self.between_blocks = []

    def _init_class_data(self):
        self.obcd_name = None # string
        self.obim_name = None # string
        self.obcd_class = None # actual class to be instantiated when reading from file
        self.obim_class = None # ditto
        raise NotImplementedError("This method must be overriden by a concrete class.")

    def add_code_block(self, block):
        if not block.obj_id in self.objects:
            self.objects[block.obj_id] = [None, None] # pos1 = image, pos2 = code
        self.objects[block.obj_id][1] = block
        self.order_map[self.obcd_name].append(block.obj_id)

    def add_image_block(self, block):
        if not block.obj_id in self.objects:
            self.objects[block.obj_id] = [None, None] # pos1 = image, pos2 = code
        self.objects[block.obj_id][0] = block
        self.order_map[self.obim_name].append(block.obj_id)

    def add_between_block(self, block):
        """Workaround for SCUMM V4 which has "SL" and "NL" blocks
        in between the OI and OC blocks."""
        self.between_blocks.append(block)

    def save_to_file(self, path):
        objects_path = os.path.join(path, self.generate_file_name())
        if not os.path.isdir(objects_path):
            os.mkdir(objects_path) # throws an exception if can't create dir
        for objimage, objcode in self.objects.values():
            # New path name = Object ID + object name (removing trailing spaces)
            obj_path_name = str(objcode.obj_id).zfill(self.obj_id_name_length) + "_" + util.discard_invalid_chars(objcode.obj_name).rstrip()
            newpath = os.path.join(objects_path, obj_path_name)
            if not os.path.isdir(newpath):
                os.mkdir(newpath) # throws an exception if can't create dir
            objimage.save_to_file(newpath)
            objcode.save_to_file(newpath)
            self._save_header_to_xml(newpath, objimage, objcode)
        self._save_order_to_xml(objects_path)
        # Workaround for V4 "SL" and "NL" blocks.
        for b in self.between_blocks:
            b.save_to_file(objects_path)

    def save_to_resource(self, resource, room_start=0):
        self._save_object_images_to_resource(resource, room_start)
        self._save_between_blocks_to_resource(resource, room_start)
        self._save_object_codes_to_resource(resource, room_start)

    def _save_object_images_to_resource(self, resource, room_start):
        object_keys = self.objects.keys()
        # Write all image blocks first
        object_keys = util.ordered_sort(object_keys, self.order_map[self.obim_name])
        for obj_id in object_keys:
            self.objects[obj_id][0].save_to_resource(resource, room_start)

    def _save_between_blocks_to_resource(self, resource, room_start):
        for b in self.between_blocks:
            b.save_to_resource(resource, room_start)

    def _save_object_codes_to_resource(self, resource, room_start):
        object_keys = self.objects.keys()
        # Write all object code/names
        object_keys = util.ordered_sort(object_keys, self.order_map[self.obcd_name])
        for obj_id in object_keys:
            self.objects[obj_id][1].save_to_resource(resource, room_start)

    def _save_header_to_xml(self, path, objimage, objcode):
        # Save the joined header information as XML
        root = et.Element("object")

        et.SubElement(root, "name").text = util.escape_invalid_chars(objcode.obj_name)
        et.SubElement(root, "id").text = util.int2xml(objcode.obj_id)

        # OBIM
        objimage.generate_xml_node(root)

        # OBCD
        objcode.generate_xml_node(root)

        util.indent_elementtree(root)
        et.ElementTree(root).write(os.path.join(path, "OBHD.xml"))

    def _save_order_to_xml(self, path):
        root = et.Element("order")

        for block_type, order_list in self.order_map.items():
            order_list_node = et.SubElement(root, "order-list")
            order_list_node.set("block-type", block_type)
            for o in order_list:
                et.SubElement(order_list_node, "order-entry").text = util.int2xml(o)

        util.indent_elementtree(root)
        et.ElementTree(root).write(os.path.join(path, "order.xml"))

    def load_from_file(self, path):
        file_list = os.listdir(path)

        re_pattern = re.compile(r"[0-9]{" + str(self.obj_id_name_length) + r"}_.*")
        object_dirs = [f for f in file_list if re_pattern.match(f) != None]
        self.order_map = { self.obcd_name : [], self.obim_name : [] }
        for od in object_dirs:
            new_path = os.path.join(path, od)

            objimage = self.obim_class(self.block_name_length, self.crypt_value)
            objimage.load_from_file(new_path)
            self.add_image_block(objimage)

            objcode = self.obcd_class(self.block_name_length, self.crypt_value)
            objcode.load_from_file(new_path)
            self.add_code_block(objcode)

        file_list = [f for f in file_list if not f in object_dirs]
        for f in file_list:
            b = control.file_dispatcher.dispatch_next_block(f)
            if b != None:
                b.load_from_file(os.path.join(path, f))
                self.between_blocks.append(b)

        self._load_order_from_xml(path)

    def _load_order_from_xml(self, path):
        order_fname = os.path.join(path, "order.xml")
        if not os.path.isfile(order_fname):
            # If order.xml does not exist, use whatever order we want.
            return

        tree = et.parse(order_fname)
        root = tree.getroot()

        loaded_order_map = self.order_map
        self.order_map = { self.obcd_name : [], self.obim_name : [] }

        for order_list in root.findall("order-list"):
            block_type = order_list.get("block-type")

            for o in order_list.findall("order-entry"):
                if not block_type in self.order_map:
                    self.order_map[block_type] = []
                self.order_map[block_type].append(util.xml2int(o.text))

            # Retain order of items loaded but not present in order.xml
            if block_type in loaded_order_map:
                extra_orders = [i for i in loaded_order_map[block_type] if not i in self.order_map[block_type]]
                self.order_map[block_type].extend(extra_orders)

    def generate_file_name(self):
        return "objects"

    def __repr__(self):
        childstr = ["obj_" + str(c) for c in self.objects.keys()]
        return "[" + self.obim_name + " & " + self.obcd_name + ", " + "[" + ", ".join(childstr) + "] " + "]"

class ScriptBlockContainer(object):
    local_scripts_name = None
    entry_script_name = None
    exit_script_name = None
    lf_name = None
    num_local_name = None

    def __init__(self, block_name_length, crypt_value, *args, **kwds):
        self.local_scripts = []
        self.encd_script = None
        self.excd_script = None
        self.block_name_length = block_name_length
        self.crypt_value = crypt_value
        self.name = "scripts"

    def append(self, block):
        if block.name == self.local_scripts_name:
            self.local_scripts.append(block)
        elif block.name == self.entry_script_name:
            self.encd_script = block
        elif block.name == self.exit_script_name:
            self.excd_script = block
        else:
            raise util.ScummPackerException("Unrecognised script type: " + str(block.name))

    def save_to_file(self, path):
        newpath = os.path.join(path, self.generate_file_name())
        if not os.path.isdir(newpath):
            os.mkdir(newpath) # throws an exception if can't create dir
        if self.encd_script:
            self.encd_script.save_to_file(newpath)
        if self.excd_script:
            self.excd_script.save_to_file(newpath)
        for s in self.local_scripts:
            s.save_to_file(newpath)

    def save_to_resource(self, resource, room_start=0):
        # Write entry and exit scripts (seperate from local scripts)
        if not self.encd_script or not self.excd_script:
            room_num = control.global_index_map.get_index(self.lf_name, (control.disk_spanning_counter, room_start))
            raise util.ScummPackerException(
                "Room #" + str(room_num) + " appears to be missing either a room entry or exit script (or both).")
        self.excd_script.save_to_resource(resource, room_start)
        self.encd_script.save_to_resource(resource, room_start)
        
        # Generate and write "number of local scripts" block
        self._write_number_of_local_scripts(resource)

        # Write all local scripts sorted by script number
        self.local_scripts.sort(cmp=lambda x,y: cmp(x.script_id, y.script_id))
        for s in self.local_scripts:
            s.save_to_resource(resource, room_start)

    def _write_number_of_local_scripts(self, resource):
        # Determine the number of local scripts
        num_local_scripts = len(self.local_scripts)
        resource.write(util.crypt(self.num_local_name, self.crypt_value)) # write the block header's name
        resource.write(util.int2str(10, 4, util.BE, self.crypt_value)) # size of this block is always 10
        resource.write(util.int2str(num_local_scripts, 2, util.LE, self.crypt_value))
            
    def load_from_file(self, path):
        file_list = os.listdir(path)

        for f in file_list:
            b = control.file_dispatcher.dispatch_next_block(f)
            if b != None: #and self.script_types: # TODO?: only load recognised scripts
                b.load_from_file(os.path.join(path, f))
                self.append(b)

    def generate_file_name(self):
        return "scripts"

    def __repr__(self):
        childstr = [str(self.encd_script), str(self.excd_script)]
        childstr.extend([str(c) for c in self.local_scripts])
        return "[Scripts, " + ", ".join(childstr) + "]"
