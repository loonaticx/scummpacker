# setup script for Scummbler

from distutils.core import setup
import py2exe

# includes for py2exe
includes=[]

opts = { 'py2exe': { 'includes':includes } }
#print 'opts',opts

setup(version = "0.0",
      description = "Scummpacker v2 WIP",
      name = "Scummpacker v2 WIP",
      author = "Laurence Dougal Myers",
      author_email = "jestarjokin@jestarjokin.net",
      console = [
        {
            "script": "scummpacker_blocks.py",
        }
      ],
      options=opts
      )