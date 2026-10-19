#!/bin/bash
# final comparison set (one UE process at a time)
D=/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/serpent; S=$D/scripts/shotr.sh
export TAILN=1 SHOTAT=14
$S F1_close20m_horns -SerpT=3 -SerpCamDist=2000 -SerpCamYaw=235 -SerpCamPitch=-8 -SerpCamAt=0.05 -SerpHorns -SerpJaw=0.35
$S F1_close20m_plain -SerpT=3 -SerpCamDist=2000 -SerpCamYaw=235 -SerpCamPitch=-8 -SerpCamAt=0.05 -SerpJaw=-0.8
$S F2_sky60m -SerpT=4 -SerpCamDist=6000 -SerpCamYaw=290 -SerpCamPitch=-4 -SerpCamAt=0.4 -SerpHorns -SerpJaw=0.2
$S F3_sky150m -SerpT=4 -SerpCamDist=15000 -SerpCamYaw=290 -SerpCamPitch=-4 -SerpCamAt=0.4 -SerpHorns
$S F4_rise_lake -SerpMode=rise -SerpT=4.6 -SerpCamDist=6500 -SerpCamYaw=70 -SerpCamPitch=-2 -SerpCamAt=0.32 -SerpHorns -SerpJaw=0.6
$S F5_chase -SerpT=4.5 -SerpCamDist=1800 -SerpChase -SerpHorns -SerpJaw=0.2
$S F6_backlit -SerpT=3 -SerpCamDist=2600 -SerpCamYaw=45 -SerpCamPitch=-6 -SerpCamAt=0.12 -SerpHorns -SerpJaw=0.35
for v in Default Bronze Storm Scan Olive; do
  $S M_$v -SerpT=3 -SerpCamDist=1500 -SerpCamYaw=250 -SerpCamPitch=-6 -SerpCamAt=0.05 -SerpJaw=0.3 -SerpMat=/Game/Twilight/Vishap/Materials/MI_Vishap_$v.MI_Vishap_$v
done
SHOTAT=100 TMO=300 TAILN=3 $S P_toggle_25m -SerpCamDist=2500 -SerpCamYaw=250 -SerpCamPitch=-6 -SerpCamAt=0.2 -SerpToggle=4 -SerpHorns
SHOTAT=100 TMO=300 TAILN=3 $S P_toggle_80m -SerpCamDist=8000 -SerpCamYaw=250 -SerpCamPitch=-6 -SerpCamAt=0.4 -SerpToggle=4 -SerpHorns
echo FINAL_DONE
