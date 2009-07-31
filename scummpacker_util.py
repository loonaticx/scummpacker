import array
# 0 = always display (errors)
# 1 = warnings, verbose
# 2 = debug
TEXT_OUTPUT_LEVEL = 1
def message(text, level=2):
    if level <= TEXT_OUTPUT_LEVEL:
        print(text)
        
def error(text):
    message(text, 0)
    
def information(text):
    message(text, 1)
    
def debug(text):
    message(text, 2)
    
    
#def write_byte(file, byte):
    #file.write()
    
def crypt(in_val, crypt_val):
    if crypt_val is None:
        return in_val
    if type(in_val) is str:
        outString = ''
        for c in in_val:
            outString += chr(ord(c) ^ crypt_val)
        return outString
    elif type(in_val) is array.ArrayType:
        for i, byte in enumerate(in_val):
            in_val[i] = byte ^ crypt_val
        return in_val
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

def int_to_str(in_val, numBytes=4, is_BE=False, crypt_val=None):
    out_val = array.array('B')
    i = 0
    while i < numBytes:
        b = (in_val >> (i * 8)) & 0xFF 
        out_val.append(b)
        i += 1
    if is_BE:
        out_val.reverse()
    if crypt_val != None:
        out_val = crypt(out_val, crypt_val)
    return out_val.tostring()


class ScummPackerException(Exception):
    pass

class ScummPackerUnrecognisedIndexException(Exception):
    pass
