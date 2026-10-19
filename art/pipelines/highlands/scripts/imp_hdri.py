import sys
sys.path.insert(0, '/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/highlands/scripts')
import unreal
from hl_common import *
import_textures([P + 'dl/hdri/industrial_sunset_02_puresky_4k.hdr', P + 'dl/hdri/evening_road_01_puresky_4k.hdr'], '/Game/Env/HDRI')
log('HDRI DONE'); unreal.SystemLibrary.quit_editor()
