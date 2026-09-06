"""Prepare a private 64 KiB C-BIOS MSX2 test profile; never copy BIOS ROMs."""
from pathlib import Path
import os,json
ROOT=Path(__file__).resolve().parents[1]
share=Path(os.environ.get('OPENMSX_SYSTEM_DATA','C:/Program Files/openMSX/share'))
original=(share/'machines/C-BIOS_MSX2_JP.xml').read_text()
assert original.count('<size>512</size>')==1
assert '<version>V9938</version>' in original and '<vram>128</vram>' in original
profile=ROOT/'work/profile'; user=profile/'user_data'
target=user/'machines/C-BIOS_MSX2_64K.xml';target.parent.mkdir(parents=True,exist_ok=True)
target.write_text(original.replace('<size>512</size>','<size>64</size>'))
print(json.dumps({'OPENMSX_HOME':str(profile),'OPENMSX_USER_DATA':str(user),'machine':'C-BIOS_MSX2_64K'},indent=2))
