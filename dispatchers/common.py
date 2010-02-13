import logging
import os
import scummpacker_util as util

class AbstractBlockDispatcher(object):
    CRYPT_VALUE = None
    BLOCK_NAME_LENGTH = None
    BLOCK_MAP = {}
    DEFAULT_BLOCK = None
    REGEX_BLOCKS = []
    ROOT_BLOCK = None

    def dispatch_and_load_from_resource(self, resource, room_start=0):
        root_block = self.ROOT_BLOCK(self.BLOCK_NAME_LENGTH, self.CRYPT_VALUE)
        root_block.load_from_resource(resource, 0)
        return root_block

    def dispatch_next_block(self, resource):
        assert type(resource) is file
        block_name = self._read_block_name(resource)
        if not self.CRYPT_VALUE is None:
            block_name = util.crypt(block_name, self.CRYPT_VALUE)
        if block_name in self.BLOCK_MAP:
            block_type = self.BLOCK_MAP[block_name]
        else:
            block_type = self._dispatch_regex_block(block_name)
            if block_type is None:
                block_type = self.DEFAULT_BLOCK
        block = block_type(self.BLOCK_NAME_LENGTH, self.CRYPT_VALUE) # instantiate the block object
        return block

    def _dispatch_regex_block(self, block_name):
        for re_pattern, block_type in self.REGEX_BLOCKS:
            if re_pattern.match(block_name) != None:
                return block_type
        return None

    def _read_block_name(self, resource):
        bname = resource.read(self.BLOCK_NAME_LENGTH)
        resource.seek(-self.BLOCK_NAME_LENGTH, os.SEEK_CUR)
        return bname

class AbstractFileDispatcher(AbstractBlockDispatcher):
    IGNORED_BLOCKS = frozenset([])

    def dispatch_and_load_from_file(self, path):
        root_block = self.ROOT_BLOCK(self.BLOCK_NAME_LENGTH, self.CRYPT_VALUE)
        root_block.load_from_file(path)
        return root_block

    def dispatch_next_block(self, block_name):
        if block_name in self.BLOCK_MAP:
            block_type = self.BLOCK_MAP[block_name]
        else:
            block_type = self._dispatch_regex_block(block_name)
            if block_type is None:
                if not block_name in self.IGNORED_BLOCKS:
                    logging.warning("Ignoring unknown file: " + str(block_name))
                return None
        block = block_type(self.BLOCK_NAME_LENGTH, self.CRYPT_VALUE)
        return block