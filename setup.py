from distutils.core import setup
import py2exe 

setup(
    console=[{
            "script": 'moodle.py',
            "icon_resources": [(1, "ICON.ico")]
              }],
    options={
        'py2exe': 
        {
            'bundle_files': 2,
            'compressed': True,
            'includes': ['lxml.etree', 'lxml._elementpath', 'gzip', 'requests'],
        }
    },
    zipfile=None,
)
