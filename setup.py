"""
py2app build script

Usage:
    python setup.py py2app
    python setup.py py2app -A   # dev/alias mode
"""
from setuptools import setup

APP = ["ruler.py"]
OPTIONS = {
    "iconfile": "ruler.icns",
    "argv_emulation": False,
    "plist": {
        "CFBundleName": "Ruler",
        "CFBundleDisplayName": "Ruler",
        "CFBundleIdentifier": "com.RulerApp.ruler",
        "NSHighResolutionCapable": True,
    },
}

setup(
    app=APP,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
