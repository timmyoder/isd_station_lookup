"""Set directories"""

import pathlib

project_root = pathlib.Path(__file__).parent

RESOURCE_DIR = project_root / 'resources'
INPUT_DIR = project_root / 'input_data'
OUTPUT_DIR = project_root / 'output_data'

for folder in [RESOURCE_DIR, INPUT_DIR, OUTPUT_DIR]:
    if not folder.exists():
        folder.mkdir()
