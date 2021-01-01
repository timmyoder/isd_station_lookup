"""Set directories"""

import pathlib

project_root = pathlib.Path(__file__).parent

RESOURCE_DIR = project_root / 'resources'

for folder in [RESOURCE_DIR]:
    if not folder.exists():
        folder.mkdir()
