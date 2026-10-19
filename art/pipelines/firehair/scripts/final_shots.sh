#!/bin/bash
# final_shots.sh -- rebuild the look-dev maps and shoot the deliverable screenshots into deliver/shots (+ 2x crops and a contact sheet)
F=$(cd "$(dirname "$0")/../.." && pwd); S=$F/deliver/scripts; O=$F/deliver/shots; mkdir -p $O
FH_MAPS=Menu,Chase,Front,Close,Orig $S/run_ue.sh $S/ue_scenes.py 1800 | grep -E "Traceback|Error:" | head -3
OUTD=$O $S/shoot.sh L_FH_Menu 1_menu_front_3m 30
OUTD=$O $S/shoot.sh L_FH_Chase 2_chase_6m_flying 30
OUTD=$O $S/shoot.sh L_FH_Front 3_front_view_5m 30
OUTD=$O SHOTS="0 0.35" $S/shoot.sh L_FH_Close 4_close_3q_head 30
OUTD=$O $S/shoot.sh L_FH_Orig 5_current_helmet_menu_3m 30
cd $O; mv 4_close_3q_head_0.png 4_close_3q_head.png; mv 4_close_3q_head_0.35.png work_anim_frame_b.png 2>/dev/null
ffmpeg -hide_banner -loglevel error -y -i 2_chase_6m_flying.png -vf "crop=480:400:560:380,scale=960:800" 2_chase_6m_flying_crop2x.png
ffmpeg -hide_banner -loglevel error -y -i 3_front_view_5m.png -vf "crop=300:340:650:400,scale=600:680" 3_front_view_5m_crop2x.png
ffmpeg -hide_banner -loglevel error -y -i 1_menu_front_3m.png -i 5_current_helmet_menu_3m.png -filter_complex "[0]crop=560:600:520:0[a];[1]crop=560:600:520:0[b];[b][a]hstack" 5_compare_current_vs_fire.png
$S/grid.sh contact_sheet.jpg 2 800 450 1_menu_front_3m.png 2_chase_6m_flying.png 3_front_view_5m.png 4_close_3q_head.png 5_current_helmet_menu_3m.png 2_chase_6m_flying_crop2x.png
ls -la $O
