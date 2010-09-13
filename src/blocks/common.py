#! /usr/bin/python
import array
import functools
import logging
import os
import re
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
        #logging.debug("Loading block from resource: " + str(start))
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
        #logging.debug("Block name: " + str(name))
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
        logging.debug("Ordering block: %s" % (rank_lookup_name))
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


class BlockGloballyIndexed(AbstractBlock):
    lf_name = None # override in concrete class
    room_name = None # override in concrete class

    def __init__(self, *args, **kwds):
        super(BlockGloballyIndexed, self).__init__(*args, **kwds)
        self.index = None
        self.is_unknown = False

    def load_from_resource(self, resource, room_start=0):
        location = resource.tell()
        super(BlockGloballyIndexed, self).load_from_resource(resource)
        try:
            room_num = control.global_index_map.get_index(self.lf_name, room_start)
            #logging.debug("room_num: %s" % room_num)
            room_offset = control.global_index_map.get_index(self.room_name, room_num) # HACK
            #logging.debug("room_offset: %s" % room_offset)
            #logging.debug("location - room_offset: %s" % (location - room_offset))
            self.index = control.global_index_map.get_index(self.name,
                                                             (room_num, location - room_offset))
            #logging.debug("room_index: %s" % self.index)
        except util.ScummPackerUnrecognisedIndexException, suie:
            logging.error(("Block \"%s\" at offset %s has no entry in the index file (.000). " + 
                          "It can not be re-packed or used in the game.") % (self.name, location))
            self.is_unknown = True
            self.index = control.unknown_blocks_counter.get_next_index(self.name)

    def save_to_resource(self, resource, room_start=0):
        # Look up the start of the current ROOM block, store
        # a mapping of this block's index and room #/offset.
        # Later on, our directories will just treat global_index_map as a list of
        # tables and go through all of the values.
        location = resource.tell()
        #logging.debug("Saving globally indexed block: " + self.name)
        #logging.debug("LFLF: " + str(control.global_index_map.items("LFLF")))
        #logging.debug("ROOM: " + str(control.global_index_map.items("ROOM")))
        room_num = control.global_index_map.get_index(self.lf_name, room_start)
        room_offset = control.global_index_map.get_index(self.room_name, room_num)
        control.global_index_map.map_index(self.name,
                                           (room_num, location - room_offset),
                                           self.index)
        super(BlockGloballyIndexed, self).save_to_resource(resource, room_start)

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

class BlockLocalScript(AbstractBlock):
    name = None # override in concrete class

    def _read_data(self, resource, start, decrypt):
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
            #if hasattr(c, 'index'):
            #    logging.debug("object " + str(c) + " has index " + str(c.index))
            #logging.debug("location: " + str(resource.tell()))
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

    def load_from_resource(self, resource, room_start=0):
        location = resource.tell()
        self._read_header(resource, True)
        self._read_data(resource, location, True)
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
        control.global_index_map.map_index(self.name, location, self.index)
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
    LFLF_NAME = NotImplementedError("This property must be overridden by inheriting classes.") # class name
    ROOM_NAME = NotImplementedError("This property must be overridden by inheriting classes.") # class name
    OFFSET_POINTS_TO_ROOM = NotImplementedError("This property must be overridden by inheriting classes.") # boolean

    def _read_data(self, resource, start, decrypt):
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
            control.global_index_map.map_index(self.LFLF_NAME, lf_offset, room_no)
            control.global_index_map.map_index(self.ROOM_NAME, room_no, room_offset) # HACK

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
        room_table = sorted(control.global_index_map.items(self.ROOM_NAME))
        num_of_rooms = len(room_table)
        resource.write(util.int2str(num_of_rooms, 1, util.LE, self.crypt_value))
        for room_num, room_offset in room_table:
            room_num = int(room_num)
            resource.write(util.int2str(room_num, 1, util.LE, self.crypt_value))
            resource.write(util.int2str(room_offset, 4, util.LE, self.crypt_value))

    def write_dummy_block(self, resource, num_rooms):
        """This method should be called before save_to_resource. It just
        reserves space until the real block is written.

        The reason for doing this is that the block begins at the start of the
        resource file, but contains the offsets of all of the room blocks, which
        won't be known until after they've all been written."""
        block_start = resource.tell()
        self._write_dummy_header(resource, True)
        resource.write(util.int2str(num_rooms, 1, util.BE, self.crypt_value))
        for _ in xrange(num_rooms):
            resource.write("\x00" * 5)
        block_end = resource.tell()
        self.size = block_end - block_start
    
class BlockRoom(BlockContainer): # also globally indexed
    def __init__(self, *args, **kwds):
        super(BlockRoom, self).__init__(*args, **kwds)
        self._init_class_data()

    def _init_class_data(self):
        self.name = None
        self.lf_name = None
        self.script_types = frozenset()
        self.object_types = frozenset()
        self.object_image_type = None
        self.object_code_type = None
        self.num_scripts_type = None
        self.script_container_class = ScriptBlockContainer
        self.object_container_class = ObjectBlockContainer
        raise NotImplementedError("This method must be overriden by a concrete class.")

    def _read_data(self, resource, start, decrypt):
        end = start + self.size
        object_container = self.object_container_class(self.block_name_length, self.crypt_value)
        script_container = self.script_container_class(self.block_name_length, self.crypt_value)
        while resource.tell() < end:
            block = control.block_dispatcher.dispatch_next_block(resource)
            block.load_from_resource(resource)
            if block.name in self.script_types:
                script_container.append(block)
            elif block.name == self.object_image_type:
                object_container.add_image_block(block)
            elif block.name == self.object_code_type:
                object_container.add_code_block(block)
            elif block.name == self.num_scripts_type: # ignore this since we can generate it
                del block
                continue
            else:
                self.append(block)
        self.append(object_container)
        self.append(script_container)

    def save_to_resource(self, resource, room_start=0):
        location = resource.tell()
        logging.debug("Saving room")
        room_num = control.global_index_map.get_index(self.lf_name, room_start)
        control.global_index_map.map_index(self.name, room_num, location)
        super(BlockRoom, self).save_to_resource(resource, room_start)


class BlockIndexDirectory(AbstractBlock):
    """ Generic index directory """
    DIR_TYPES = NotImplementedError("This property must be overridden by inheriting classes.")
    MIN_ENTRIES = NotImplementedError("This property must be overridden by inheriting classes.")

    def _read_data(self, resource, start, decrypt):
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
    HAS_OBJECT_CLASS_DATA = NotImplementedError("This property must be overridden by inheriting classes.")

    def _read_data(self, resource, start, decrypt):
        num_items = util.str2int(resource.read(2), crypt_val=(self.crypt_value if decrypt else None))
        self.objects = []
        # Write all owner+state values
        for _ in xrange(num_items):
            owner_and_state = util.str2int(resource.read(1), crypt_val=(self.crypt_value if decrypt else None))
            owner = (owner_and_state & 0xF0) >> 4
            state = owner_and_state & 0x0F
            self.objects.append([owner, state])
        # Write all class data values
        if self.HAS_OBJECT_CLASS_DATA:
            for i in xrange(num_items):
                class_data = util.str2int(resource.read(4), crypt_val=(self.crypt_value if decrypt else None))
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
            if self.HAS_OBJECT_CLASS_DATA:
                class_data = util.xml2int(obj_node.find("class-data").text)
                self.objects.append([owner, state, class_data])
            else:
                self.objects.append([owner, state])

    def save_to_file(self, path):
        root = et.Element("object-directory")

        for i in xrange(len(self.objects)):
            if self.HAS_OBJECT_CLASS_DATA:
                owner, state, class_data = self.objects[i]
            else:
                owner, state = self.objects[i]
            obj_node = et.SubElement(root, "object-entry")
            et.SubElement(obj_node, "id").text = util.int2xml(i + 1)
            et.SubElement(obj_node, "owner").text = util.int2xml(owner)
            et.SubElement(obj_node, "state").text = util.int2xml(state)
            if self.HAS_OBJECT_CLASS_DATA:
                et.SubElement(obj_node, "class-data").text = util.hex2xml(class_data)

        util.indent_elementtree(root)
        et.ElementTree(root).write(os.path.join(path, "dobj.xml"))

    def save_to_resource(self, resource, room_start=0):
        """ TODO: allow filling of unspecified values (e.g. if entries for
        86 and 88 exist but not 87, create a dummy entry for 87."""
        num_items = len(self.objects)

        if self.HAS_OBJECT_CLASS_DATA:
            entry_size = 5
        else:
            entry_size = 1
        self.size = entry_size * num_items + 2 + self.block_name_length + 4
        self._write_header(resource, True)

        resource.write(util.int2str(num_items, 2, crypt_val=self.crypt_value))
        if self.HAS_OBJECT_CLASS_DATA:
            for owner, state, _ in self.objects:
                combined_val = ((owner & 0x0F) << 4) | (state & 0x0F)
                resource.write(util.int2str(combined_val, 1, crypt_val=self.crypt_value))
            for _, _, class_data in self.objects:
                resource.write(util.int2str(class_data, 4, crypt_val=self.crypt_value))
        else:
            for owner, state, in self.objects:
                combined_val = ((owner & 0x0F) << 4) | (state & 0x0F)
                resource.write(util.int2str(combined_val, 1, crypt_val=self.crypt_value))
                
class BlockRoomIndexes(AbstractBlock):
    """Don't really seem to be used much for V5 and LOOM CD.

    Each game seems to have a different padding length."""
    name = NotImplementedError("This property must be overridden by inheriting classes.")
    DEFAULT_PADDING_LENGTHS = NotImplementedError("This property must be overridden by inheriting classes.")

    def __init__(self, *args, **kwds):
        # default padding length is 127 for now
        self.padding_length = kwds.get('padding_length',
                                       self.DEFAULT_PADDING_LENGTHS[control.global_args.game])
        super(BlockRoomIndexes, self).__init__(*args, **kwds)

    """Directory of offsets to ROOM blocks."""
    def save_to_file(self, path):
        """This block is generated when saving to a resource."""
        return

    def save_to_resource(self, resource, room_start=0):
        """DROO blocks do not seem to be used in V5 games, so save dummy info."""
#        room_num = control.global_index_map.get_index("LFLF", room_start)
#        room_offset = control.global_index_map.get_index("ROOM", room_num)
        self.size = 5 * self.padding_length + 2 + self.block_name_length + 4
        self._write_header(resource, True)
        resource.write(util.int2str(self.padding_length, 2, crypt_val=self.crypt_value))
        for _ in xrange(self.padding_length): # this is "file/disk number" rather than "room number" in V4
            resource.write(util.int2str(0, 1, crypt_val=self.crypt_value))
        for _ in xrange(self.padding_length):
            resource.write(util.int2str(0, 4, crypt_val=self.crypt_value))
                

class BlockRoomNames(AbstractBlock):
    name_length = 9
    name = NotImplementedError("This property must be overridden by inheriting classes.")

    def _read_data(self, resource, start, decrypt):
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

    def save_to_file(self, path):
        objects_path = os.path.join(path, self.generate_file_name())
        if not os.path.isdir(objects_path):
            os.mkdir(objects_path) # throws an exception if can't create dir
        for objimage, objcode in self.objects.values():
            # New path name = Object ID + object name (removing trailing spaces)
            obj_path_name = str(objcode.obj_id).zfill(self.obj_id_name_length) + "_" + util.discard_invalid_chars(objcode.obj_name).rstrip()
            #logging.debug("Writing object: %s" % obj_path_name)
            newpath = os.path.join(objects_path, obj_path_name)
            if not os.path.isdir(newpath):
                os.mkdir(newpath) # throws an exception if can't create dir
            objimage.save_to_file(newpath)
            objcode.save_to_file(newpath)
            self._save_header_to_xml(newpath, objimage, objcode)
        self._save_order_to_xml(objects_path)

    def save_to_resource(self, resource, room_start=0):
        object_keys = self.objects.keys()
        # Write all image blocks first
        object_keys = util.ordered_sort(object_keys, self.order_map[self.obim_name])
        for obj_id in object_keys:
            #logging.debug("Writing object image: " + str(obj_id))
            self.objects[obj_id][0].save_to_resource(resource, room_start)

        # Then write all object code/names
        object_keys = util.ordered_sort(object_keys, self.order_map[self.obcd_name])
        for obj_id in object_keys:
            #logging.debug("Writing object code: " + str(objcode.obj_id))
            self.objects[obj_id][1].save_to_resource(resource, room_start)

    def _save_header_to_xml(self, path, objimage, objcode):
        # Save the joined header information as XML
        root = et.Element("object")

        #shared = et.SubElement(root, "shared")
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
        # Determine the number of local scripts
        num_local_scripts = len(self.local_scripts)
        # Write entry and exit scripts (seperate from local scripts)
        if not self.encd_script or not self.excd_script:
            room_num = control.global_index_map.get_index(self.lf_name, room_start)
            raise util.ScummPackerException(
                "Room #" + str(room_num) + " appears to be missing either a room entry or exit script (or both).")
        self.excd_script.save_to_resource(resource, room_start)
        self.encd_script.save_to_resource(resource, room_start)
        # Generate and write "number of local scripts" block (could be prettier, should have its own class)
        resource.write(util.crypt(self.num_local_name, self.crypt_value))
        resource.write(util.int2str(10, 4, util.BE, self.crypt_value)) # size of this block is always 10
        resource.write(util.int2str(num_local_scripts, 2, util.LE, self.crypt_value))
        # Write all local scripts sorted by script number
        self.local_scripts.sort(cmp=lambda x,y: cmp(x.script_id, y.script_id))
        for s in self.local_scripts:
            s.save_to_resource(resource, room_start)

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

class XMLHelper(object):
    def __init__(self):
        self.read_actions = {
            'i' : functools.partial(self._read_value_from_xml_node, marshaller=util.xml2int), # int
            'h' : functools.partial(self._read_value_from_xml_node, marshaller=util.xml2int), # hex
            's' : functools.partial(self._read_value_from_xml_node, marshaller=util.escape_invalid_chars), # string
            'n' : self.read # node
        }
        self.write_actions = {
            'i' : functools.partial(self._write_value_to_xml_node, marshaller=util.int2xml), # int
            'h' : functools.partial(self._write_value_to_xml_node, marshaller=util.hex2xml), # hex
            's' : functools.partial(self._write_value_to_xml_node, marshaller=util.unescape_invalid_chars), # string
            'n' : self.write # node
        }

    def read(self, destination, parent_node, structure):
        for name, marshaller, attr in structure:
            node = parent_node.find(name)
            self.read_actions[marshaller](destination, node, attr)

    def _read_value_from_xml_node(self, destination, node, attr, marshaller):
        value = marshaller(node.text) # doesn't support "attributes" of nodes, just values
        # Get nested attributes
        attr_split = attr.split(".")
        destination = reduce(lambda a1, a2: getattr(a1, a2), attr_split[:-1], destination)
        attr = attr_split[-1]
        setattr(destination, attr, value)

    def _write_value_to_xml_node(self, caller, node, attr, marshaller):
        # Get nested attributes
        attr = reduce(lambda a1, a2: getattr(a1, a2), attr.split("."), caller)
        node.text = marshaller(attr)

    def write(self, caller, parent_node, structure):
        for name, marshaller, attr in structure:
            node = et.SubElement(parent_node, name)
            self.write_actions[marshaller](caller, node, attr)
