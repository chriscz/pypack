import sys
import os
import re
import argparse
import base64                                        
import inspect

# variables used during unpacking
basename = '.pypack'
HOME = os.path.expanduser('~/')
BASHRC = os.path.join(HOME, '.bashrc')
BASE = os.path.join(HOME, basename) 
BIN = os.path.join(BASE, 'bin/') 
LIB = os.path.join(BASE, 'lib/') 


# variables used during packing
magic_exec = [
    b'^\x7fELF.{12}\x02\x00'
]
magic_lib  = [
    b'^\x7fELF.{12}\x03\x00'
]

def re_compiled(patternlist):
    compiled = []
    for p in patternlist:
        compiled.append(re.compile(p))
    return compiled
# compile all the patterns
magic_exec = re_compiled(magic_exec)
magic_lib = re_compiled(magic_lib)

def matches(patterns, string):
    return any(p.match(string) for p in patterns)

def hexlify(string):
    hexed = []
    for i in string:
        s = str(hex(ord(i)))[2:]
        s = s if len(s) > 1 else '0' + s
        hexed.append(s)
    return ' '.join(hexed)            

def main_pack(binaries):
    packed = {
        'executables': [],
        'libraries': []
    }
    seen = set()
    for path in binaries:
        name = os.path.basename(path)
        assert name not in seen, 'duplicate binary name %s (%s)' % (name, path) 
        seen.add(name)

        with open(path, 'rb') as exe:
            binary = exe.read()
            encoded = base64.b64encode(binary)

        sys.stderr.write("processing: {}\n".format(path))
        if matches(magic_exec, binary):
            packed['executables'].append((name, encoded))
        elif matches(magic_lib, binary):
            packed['libraries'].append((name, encoded))
        else:
            raise RuntimeError("unhandled magic:", hexlify(binary[:18]))
        
    # write the script to stdout
    sys.stdout.write('packed = {}\n\n'.format(repr(packed)))
    for line in open(__file__, 'r'):
        sys.stdout.write(line)
    sys.stdout.flush()


# --- code for unpacking
def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def prepare_home(config):
    ensure_dir(config['bin'])
    ensure_dir(config['lib'])
    
    re_comment = re.compile('#pypack:{}'.format(re.escape(config['basename'])))

    # ensure that pypack is on the path, if not add it
    with open(config['bashrc'], 'r+') as f:
        bashrc = f.read()
        if not re_comment.search(bashrc):
            f.write('PATH="$PATH"{os.pathsep}"{config[bin]}" #pypack:{config[basename]}\n'.format(os=os, config=config))

def decode_data_to(data, filename, make_exec=True):
    data = base64.b64decode(data)
    with open(filename, 'w') as f:
        data = f.write(data)
        f.flush()
    f.close()

    if make_exec:
        os.chmod(filename, 0700)
    else:
        os.chmod(filename, 0600)

def main_unpack(config, packed):
    prepare_home(config)

    for (fname, data) in packed['executables']:
        decode_data_to(data, os.path.join(config['bin'], fname))    

    for (fname, data) in packed['libraries']:
        decode_data_to(data, os.path.join(config['lib'], fname), make_exec=False)    

if __name__ == '__main__':
    if 'packed' not in globals():
        parser = argparse.ArgumentParser(description='Packs executables and shared libraries into a single python file')
        parser.add_argument('binary', nargs='+')
        args = parser.parse_args()
        main_pack(args.binary)
    else:
        config = dict(
            basename=basename,
            base=BASE,
            bin=BIN,
            lib=LIB,
            bashrc=BASHRC
        )
        main_unpack(config, packed)
