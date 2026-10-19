import sys
sys.path.insert(0, '/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/highlands/scripts')
import unreal
from hl_common import *
import_textures([GEN + 'tex/T_core_Canopy.png', GEN + 'tex/T_Black.png'], '/Game/Terrain/Maps')
log('EXTRA DONE')
unreal.SystemLibrary.quit_editor()
