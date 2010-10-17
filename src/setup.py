# setup script for ScummPacker

from distutils.core import setup
import py2exe

# includes for py2exe
includes=[]

opts = { 'py2exe': { 'includes':includes } }
#print 'opts',opts

setup(version = "2.0",
      description = "Scummpacker v2",
      name = "Scummpacker v2",
      author = "Laurence Dougal Myers",
      author_email = "jestarjokin@jestarjokin.net",
      console = [
        {
            "script": "scummpacker.py",
        }
      ],
      options=opts
      )