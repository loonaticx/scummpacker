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
            room_offset = control.global_index_map.get_index(self.room_name, room_num) # HACK
            self.index = control.global_index_map.get_index(self.name,
                                                             (room_num, location - room_offset))
        except util.ScummPackerUnrecognisedIndexException, suie:
            logging.error("Block \""
                       + str(self.name)
                       + "\" at offset "
                       + str(location)
                       + " has no entry in the index file (.000). "
                       + "It can not be re-packed or used in the game.")
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
        self.script_id = util.str_to_int(script_id)
        self.data = self._read_raw_data(resource, self.size - (resource.tell() - start), decrypt)

    def _write_data(self, outfile, encrypt):
        script_num = util.int_to_str(self.script_id, num_bytes=1)
        if encrypt:
            script_num = util.crypt(script_num, self.crypt_value)
        outfile.write(script_num)
        self._write_raw_data(outfile, encrypt)

    def generate_file_name(self):
        return self.name + "_" + str(self.script_id).zfill(3) + ".dmp"

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
            logging.error("Block \""
                       + str(self.name)
                       + "\" at offset "
                       + str(location)
                       + " has no entry in the index file (.000). "
                       + "It can not be re-packed or used in the game without manually assigning an index.")
            self.is_unknown = True
            self.index = control.unknown_blocks_counter.get_next_index(self.name)

    def save_to_resource(self, resource, room_start=0):
        location = resource.tell()
        room_start = location
        control.global_index_map.map_index(self.name, location, self.index)
        super(BlockLucasartsFile, self).save_to_resource(resource, room_start)

    def save_to_file(self, path):
        logging.info("Saving block "
                         + self.name
                         + ":"
                         + ("unk_" if self.is_unknown else "")
                         + str(self.index).zfill(3))
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

    def _read_data(self, resource, start, decrypt):
        end = start + self.size
        #object_container = self.object_container_class(self.block_name_length, self.crypt_value)
        script_container = self.script_container_class(self.block_name_length, self.crypt_value)
        while resource.tell() < end:
            block = control.block_dispatcher.dispatch_next_block(resource)
            block.load_from_resource(resource)
            if block.name in self.script_types:
                script_container.append(block)
#            elif block.name == self.object_image_type:
#                object_container.add_image_block(block)
#            elif block.name == self.object_code_type:
#                object_container.add_code_block(block)
            elif block.name == self.num_scripts_type: # ignore this since we can generate it
                del block
                continue
            else:
                self.append(block)
        #self.append(object_container)
        self.append(script_container)

    def save_to_resource(self, resource, room_start=0):
        location = resource.tell()
        logging.debug("Saving room")
        room_num = control.global_index_map.get_index(self.lf_name, room_start)
        control.global_index_map.map_index(self.lf_name, room_num, location)
        super(BlockRoom, self).save_to_resource(resource, room_start)

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
        resource.write(util.int_to_str(10, 4, util.BE, self.crypt_value)) # size of this block is always 10
        resource.write(util.int_to_str(num_local_scripts, 2, util.LE, self.crypt_value))
        # Write all local scripts sorted by script number
        self.local_scripts.sort(cmp=lambda x,y: cmp(x.script_id, y.script_id))
        for s in self.local_scripts:
            s.save_to_resource(resource, room_start)

    def load_from_file(self, path):
        file_list = os.listdir(path)

        for f in file_list:
            b = control.file_dispatcher.dispatch_next_block(f)
            if b != None: #and self.script_types: #TODO: only load recognised scripts
                b.load_from_file(os.path.join(path, f))
                self.append(b)

    def generate_file_name(self):
        return "scripts"

    def __repr__(self):
        childstr = [str(self.encd_script), str(self.excd_script)]
        childstr.extend([str(c) for c in self.local_scripts])
        return "[Scripts, " + ", ".join(childstr) + "]"