import array
import string
import copy

__valid_file_chars = frozenset("-_.() %s%s" % (string.ascii_letters, string.digits)) # for filenames
__valid_text_chars = frozenset("!@#$%s&*+\"';:,-_.() %s%s" % ("%", string.ascii_letters, string.digits)) # for XML files
    
def crypt(in_val, crypt_val):
    if crypt_val is None:
        return in_val
    if type(in_val) is str:
        out_string = ''
        for c in in_val:
            out_string += chr(ord(c) ^ crypt_val)
        return out_string
    elif type(in_val) is array.ArrayType:
        out_val = copy.deepcopy(in_val)
        for i, byte in enumerate(out_val):
            out_val[i] = byte ^ crypt_val
        return out_val
    raise ScummPackerException("Could not encrypt values of type: " + str(type(in_val)))

LE = False
BE = True
def str_to_int(in_val, is_BE=False, crypt_val=None):
    out_val = 0
    if crypt_val != None:
        in_val = crypt(in_val, crypt_val)
    if is_BE:
        in_val = reversed(in_val)
    for i, c in enumerate(in_val):
        out_val += ord(c) << (i * 8)
    return out_val

def int_to_str(in_val, num_bytes=4, is_BE=False, crypt_val=None):
    out_val = array.array('B')
    i = 0
    while i < num_bytes:
        b = (in_val >> (i * 8)) & 0xFF 
        out_val.append(b)
        i += 1
    if is_BE:
        out_val.reverse()
    if crypt_val != None:
        out_val = crypt(out_val, crypt_val)
    return out_val.tostring()

def parse_int_from_xml(in_str):
    if in_str.startswith("0x"):
        return int(in_str, 16)
    else:
        return int(in_str)

def output_int_to_xml(in_val):
    return str(in_val)

def output_hex_to_xml(in_val):
    return hex(in_val).rstrip('L')

def discard_invalid_chars(in_str):
    return ''.join([c for c in in_str if c in __valid_file_chars])

def escape_invalid_chars(in_str):
    return ''.join([(c if c in __valid_text_chars else ('\\x' + hex(ord(c)).lstrip("0x").rstrip("L").zfill(2))) for c in in_str])

def unescape_invalid_chars(in_str):
    out_string = ""
    # Is there a more Pythonic way to do this?
    i = 0
    while i < len(in_str):
        c = in_str[i]
        if c == '\\':
            # Valid escape codes are:
            # "\xFF" for hex values
            # "\\" for backslashes
            # "\"" for quote marks
            # We treat any unknown escape codes as if the backslash did not exist.
            i += 1
            c = in_str[i]
            if c == 'x':
                # 'x' represents hex values, such as "\xFF"
                i += 1
                c2 = in_str[i]
                i += 1
                c3 = in_str[i]
                esc_val = int(c2 + c3, 16)
                c = chr(esc_val)
        out_string += c
        i+= 1
    return out_string

def indent_elementtree(elem, level=0):
    """ This function taken from http://effbot.org/zone/element-lib.htm#prettyprint.
    By Fredrik Lundh & Paul Du Bois."""
    i = "\n" + (level * "  ")
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for child in elem:
            indent_elementtree(child, level+1)
        if not child.tail or not child.tail.strip():
            child.tail = i
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def ordered_sort(in_list, order):
    """ Takes a list of values and a list containing the order of those values. Wait,
    this is retarded. Don't use it."""
    # This is a bit silly; could probably just use keys from "order" instead of
    #  sorting at all.
    INFINITY = len(in_list) # append unrecognised values to end
    deco = [ ((order.index(v) if v in order else INFINITY), i, v) for i, v in enumerate(in_list) ]
    deco.sort()
    return [ v for _, _, v in deco ]

class ScummPackerException(Exception):
    pass

class ScummPackerUnrecognisedIndexException(ScummPackerException):
    pass

def __test():
    m = [101, 102, 103, 104, 107, 106, 105] # values
    o = [105, 104, 101, 102, 103] # sorted order
    assert ordered_sort(m, o) == [105, 104, 101, 102, 103, 107, 106]

if __name__ == '__main__': __test()