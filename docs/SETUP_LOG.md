# Twilight — մրցույթի նախագծի մատյան

## 2026-10-18 — Քայլ 1. Մրցույթի պայմաններ, գործիքների ակտիվացում
- **Ինչ եղավ.** Օգտատերը (4-րդ կուրսի ծրագրավորման ուսանող) ուղարկեց Twilight-ի (twilight.ecaf@gmail.com) նամակը։ Թեմա՝ «Թռիչք դեպի դիցաբանության խորքերը»։ Ձևաչափ՝ խաղ կամ վեբկայք, ~1 շաբաթ։ Առաջին 2 օրը ամենօրյա առաջընթացը՝ Gmail-ով (սքրինշոթ + կարճ նկարագրություն), հետո՝ կայքում։
- **Պահանջ.** Կոդ ՉԳՐԵԼ․ նախ քննարկել, ակտիվացնել սկիլները, սպասել կայքի մասին տեղեկությանը (երկրորդ հաղորդագրություն)։
- **Արված.** Բեռնվեց «hayeren» սկիլը։ Ստուգվեց պանակը՝ /var/www/html/Twilight դատարկ է, git չէ։ Ստեղծվեց այս ֆայլը։
- **Առաջարկված ուղղություններ.** (1) խաղ «Հարդագողի ճանապարհ» (Վահագն, Ծիր Կաթին), (2) կայք-ատլաս հայկական դիցարանի, (3) հիբրիդ՝ scroll-«թռիչք» կայք + 1 խաղ (խորհուրդ տրված)։
- **Արդյունք.** Սպասում ենք մրցույթի կայքի տվյալներին և կանոններին։ Կոդ չի գրվել։

## 2026-10-18 — Քայլ 2. Պատասխաններ և կոնցեպտի խորացում
- **Օգտատիրոջ պատասխաններ.** ժամկետ՝ 1 շաբաթ, AI-ն ամբողջությամբ թույլատրված է, թիմը՝ միայն ինքը, մրցույթի կայքում այլ տեղեկություն չկա։ Թեման (և «Հարդագողի» գաղափարը) թույլ է համարում, նախընտրում է խաղ, հիբրիդը չի պատկերացնում։
- **Առաջարկված.** 3 կոնցեպտ՝ (1) «Վահագն. Կրակե պատանի»՝ թռիչք ծիրանի ծովի խորքից դեպի երկինք, վիշապների դեմ մարտ (խորհուրդ տրված), (2) «Արալեզ»՝ իջնել ստորերկրյա աշխարհ Արային վերադարձնելու համար, (3) «Դիցերի աշտարակ»՝ ամեն հարկը՝ մեկ դիցաբանություն։ Ձևաչափ՝ խաղը գլխավորն է, և մեկէջանոց կայքը նրա «տունն» է (Դիցարանը բացվում է խաղալիս)։
- **Արդյունք.** Սպասում ենք կոնցեպտի ընտրությանը և տեխնոլոգիաների մասին պատասխանին։ Կոդ չի գրվել։

## 2026-10-18 — Քայլ 3. Երեք խաղ, տեխնոլոգիաներ, պլան
- **Օգտատեր.** ուզում է երեք կոնցեպտն էլ որպես երեք խաղ։ Լեզվի սահմանափակում չունի (C++, C#, JS, Python, React), կոդը գրում է AI-ով։
- **Արված.** Ստեղծվեց `docs/PLAN_hy.md`՝ կառուցվածք (3 խաղ + կայք + ընդհանուր Դիցարան), տեխնոլոգիաներ (TS + Vite + Phaser, monorepo), օր առ օր օրացույց, «հաջորդականության» կանոն։
- **Արդյունք.** Սպասում ենք պլանի հաստատմանը, ճշգրիտ ժամկետին և կոնցեպտ-արտի թույլտվությանը։ Կոդ չի գրվել։

## 2026-10-18 — Քայլ 4. Շարժիչի ընտրություն, Աշտարակի փոխարինում
- **Օգտատեր.** կասկածում է, որ TS/վեբով լավ էֆեկտներ չեն ստացվի, թույլ է տալիս ծանր խաղ/հավելված (կտեղադրի իր սերվերում)։ Աշտարակը (հանելուկներ) քիչ էքշն ունի։ Խնդրեց, որ ես որոշեմ պրոֆեսիոնալ կերպով։
- **Ստուգում (`lspci; free -h; df -h; nproc`).** GPU՝ Intel Iris Xe (ինտեգրված), RAM՝ 30 ԳԲ, ազատ սկավառակ՝ 42 ԳԲ (91% լցված), 20 միջուկ։ Godot, Unity, Unreal, Blender տեղադրված չեն։
- **Որոշում (առաջարկ).** Godot 4 (GDScript), Forward+ renderer՝ desktop build-երի համար (Windows/Linux) + թեթև վեբ տարբերակ + թրեյլեր։ Unreal-ը մերժված է (Iris Xe, ծավալ, Blueprints), Unity-ն՝ editor-ի կախվածության պատճառով։ Աշտարակը փոխարինվում է «Հայկ. Նետի թռիչք» խաղով։ 3 խաղը՝ 3 գլուխ մեկ ընդհանուր հիմքի վրա։
- **Արդյունք.** Սպասում ենք հաստատմանը։ Կոդ չի գրվել։

## 2026-10-18 — Քայլ 5. Unreal Engine-ի ստուգում
- **Օգտատեր.** «on my laptop there is unreal»։
- **Ստուգում.** `find`/`du`՝ `~/UnrealEngine-5.8` (5.8.2, source build, 165 ԳԲ, UnrealEditor կա), PythonScriptPlugin կա։ Նախկին նախագիծ՝ `~/Documents/ChatGPT/Fight Game` (UE 5.8, C++, 24 ԳԲ, Codex-ով, build/run՝ հրամանային տողից)։ Դրա `DefaultEngine.ini`-ում արագության համար իջեցված է՝ `r.ScreenPercentage=70`, `r.VolumetricFog=0`, `r.ShadowQuality=2` (Iris Xe)։
- **Վեբ ստուգում.** Epic-ի փաստաթղթերով Windows build-ը Linux-ից հնարավոր չէ (cross-compile միայն Windows → Linux)։
- **Եզրակացություն.** Godot-ի դեմ իմ 2 փաստարկը (տեղադրում, AI-ի կառավարելիություն) թուլացավ։ Մնում են՝ Windows build-ի խնդիրը, Iris Xe-ի արագությունը, 42 ԳԲ ազատ տեղը։ Առաջարկ՝ Unreal, եթե կա Windows համակարգիչ, + վաղը առավոտյան 1–2 ժամանոց արագության թեստ (spike)։

## 2026-10-18 — Քայլ 6. Fight Game-ի ջնջում, շարժիչը՝ Unreal
- **Օգտատեր.** ջնջել Fight Game-ն ամբողջությամբ, Windows build պետք չէ (կներկայացնի իր նոութբուքից), ուզում է երեք ամբողջական, «մեծ» խաղ։
- **Նախքան ջնջելը.** `git remote -v` → origin https://github.com/Samvel10/FightGame.git, ճյուղ `feature/combat-simulation-core` (համաժամեցված), 2 չպահպանված փոփոխություն (`FightFighterCharacter.cpp/.h`)։ Գործարկված պրոցես չկար։
- **Հրաման.** `rm -rf "$HOME/Documents/ChatGPT/Fight Game"`։ Արդյունք՝ ազատ տեղը 42 → 65 ԳԲ։ GitHub-ի repo-ն ՉԻ ջնջվել։
- **Որոշում.** Շարժիչ՝ Unreal Engine 5.8.2 (Linux, ներկայացումը՝ օգտատիրոջ նոութբուքից)։ Վաղը՝ արագության թեստ (կարգավորումների համար)։

## 2026-10-18 — Քայլ 7. Նոր ժամկետ, repo, կոնցեպտ-արտ, նամակի սևագիր
- **Օգտատեր.** ներկայացում՝ **10-22** (օրական 1 խաղ), Higgsfield կրեդիտ չկա → նկարները ստեղծել ինքս, GitHub repo՝ թույլատրված։ Խաղի ձևաչափ՝ 5–10 րոպեանոց մրցախաղեր, 1–3 աշխարհ, ռոբոտներ/այլ խաղացողներ, հաղթանակ/պարտություն։ Ուզում է պրոֆեսիոնալ որակ, առանց «հիմար» բագերի։
- **Ստուգում.** UE-ում կան TP_ThirdPerson (C++), StarterContent, Water, PCG, GeometryScripting, PythonScriptPlugin։ Տեղում՝ Chrome, ffmpeg, PIL/numpy, Noto Armenian տառատեսակներ, `gh` (Samvel10)։
- **Repo.** `git init -b main`, տեղային identity՝ Samvel10 / samvelkhachatryan167@gmail.com (global config չի փոխվել), `gh repo create Samvel10/Twilight --private --source=. --push`։
- **Պլան.** `docs/PLAN_hy.md` վերագրված՝ 3 մրցախաղ (Վահագն 10-19, Հայկ 10-20, Արալեզ 10-21), որակի դարպաս (7 կետ)։
- **Կոնցեպտ-արտ.** `art/keyart/keyart.html` + `scenes.js` (canvas, procedural), ռենդեր՝ `google-chrome --headless=new --screenshot`։ 3 անցում (1-ին՝ կոպիտ սիլուետներ, 2-րդ՝ կմախքով կերպարներ + հալված կրակի shader, 3-րդ՝ համամասնություններ)։ Արդյունք՝ `vahagn/hayk/aralez.png|jpg`։ Commit `5b8930c`։
- **Gmail.** Սևագիր twilight.ecaf@gmail.com-ին (id r121853156790753139), առանց կցորդների (նկարները կցում է օգտատերը)։ ՉԻ ուղարկվել։

## 2026-10-18 20:33 — research subagent: Niagara/Cascade VFX plan
- Wrote /var/www/html/Twilight/docs/research/01_niagara_vfx.md (read-only engine research; no project files touched, editor not launched).
- Key: Niagara templates have no User params; use StarterContent Cascade (P_Fire/P_Explosion/P_Sparks) + DMXFixtures Niagara (VFX_Shell_Peony, VFX_Trail_Comet, ColdSparks, WaterJet with User params) + C++ point lights + Python-made emissive materials as fallback.

## 2026-10-18 20:36 — Research 04: testing / perf / capture on Linux (subagent)
- **What:** research report at `docs/research/04_test_perf_linux.md` (no project files changed, editor not launched).
- **Commands run (read-only):** `echo $XDG_SESSION_TYPE $DISPLAY` → x11 :0; `vulkaninfo --summary` → Iris Xe (RPL-P), Mesa 25.2.8; `powerprofilesctl get` → balanced; 2-s `ffmpeg -f x11grab` test in the scratchpad (OK, deleted); greps of the engine source for flags/APIs.
- **Key results:** `-seconds=N` auto-quit (non-Shipping); `-benchmark` forces a fixed timestep (do not use for FPS); CSV → `Saved/Profiling/CSV`; editor-binary screenshots → `Saved/Screenshots/LinuxEditor`; scalability cvars must not go in [SystemSettings] (priority trap); no game target is built yet → first package needs a full engine compile (hours).
- **Outcome:** done; UNVERIFIED items listed in section 7 of the report.

### 2026-10-18 20:41 — Research: headless materials (subagent)
- What: verified MaterialEditingLibrary/MaterialFactoryNew/AssetTools APIs in UE 5.8 source; wrote `docs/research/02_materials_python.md` and `docs/research/materials_build.py`.
- Commands: `python3 -m py_compile docs/research/materials_build.py` (OK); mock run with stub `unreal` module (OK, 0 errors). No UE launched, Game/ untouched.
- Run: `UnrealEditor-Cmd Game/Twilight.uproject -run=pythonscript -script=<abs>/materials_build.py -unattended -nop4 -nosplash -nosound -stdout`.
- Findings: pin "Input" must be passed as "" ; Power exponent pin is "Exp"; MI param setters always return False; InitialParent not settable from Python; shaders not verified in commandlet (check log on first launch).

### 2026-10-18 20:42 — Research 03 (subagent): flight & gameplay C++ architecture
- Output: docs/research/03_flight_gameplay_cpp.md
- Method: read-only grep of /home/samo/UnrealEngine-5.8 headers/sources, strings on template .uasset files, fc-query on Noto fonts. No build, no editor launch, nothing written under Game/.
- Key findings: DefaultInput.ini must set EnhancedPlayerInput/EnhancedInputComponent (engine default is legacy); UMG C++ tree must be built in RebuildWidget (NativeConstruct is too late); Noto Sans Armenian lacks digits -> runtime composite font (Roboto + Armenian subfont); Manny assets must live at /Game/Characters/Mannequins.

## 2026-10-18 (գիշեր) — Քայլ 8. Վահագն՝ Unreal նախագիծ, կոդ, ակտիվներ
- **Օգտատեր.** աշխատել ամբողջ գիշեր, առաջին խաղը պրոֆեսիոնալ մակարդակով, ինքնուրույն ստուգել. ձայնի/կրեդիտների մասին չմտահոգվել, չխնայել։
- **Workflow «vahagn-night-research»** (5 գործակալ + critic). զեկույցներ `docs/research/01–04*.md`, `materials_build.py`, ձայներ `art/audio/` (17 SFX + 3 երաժշտություն, procedural)։
- **Նախագիծ.** `Game/Twilight.uproject` (UE 5.8, C++ մոդուլ Twilight), Content-ում՝ Manny կերպարը (TemplateResources/High/Characters), StarterContent, Noto Armenian TTF-ներ (`Content/Fonts`)։ Config՝ Lumen/VSM/Nanite անջատված, Vulkan SM6։
- **C++ (≈3000 տող).** TwPoseAnimInstance (graph-less անիմացիա՝ custom proxy Evaluate, cross-fade), VahagnCharacter (թռիչք, նշանառություն camera-trace + aim assist, կրակ/լիցքավորված/Nova, autopilot թեստի համար), Fireball, Vishap (օձանման մարմին՝ trail, AI 9 վիճակ, բոս 3 փուլ), FireOrb, VahagnGameMode (մենյու→intro→3 ալիք→բոս, 8 րոպե, միավոր/ռեկորդ, -TwAutoPlay թեստ), VahagnPlayerController (Enhanced Input runtime-ում, gamepad), VahagnHud (Slate, հայերեն), VahagnWorld (մայրամուտ, մառախուղ, ծով, 15 procedural կղզի, Մասիս, վիշապաքարեր)։
- **Հավաքում.** `Build.sh TwilightEditor Linux Development` → UBT-ն վերակառուցում է շարժիչի 2694 action (պատճառը անհայտ, link.rsp-ները փոխվել են)։ Ընթացքի մեջ է։
- **Ակտիվներ.** `TwilightAssets.uproject` (առանց մոդուլի) + `Tools/build_assets.py` → 7 նյութ, 13 MI, 20 ձայն, 4 մակարդակ, 0 սխալ (`docs/logs/build_assets_1.log`)։
- **Workflow «vahagn-code-review»** (4 վերանայող + ստուգողներ) գործարկված՝ հավաքումից առաջ սխալներ գտնելու համար։

## 2026-10-18 21:23 — Critic review of research reports 01–04 + materials_build.py (subagent)
- **What:** verified every API, flag and asset-path claim in docs/research/01–04 and materials_build.py against the UE 5.8 source/content on disk, read-only (no editor launched, nothing changed in Game/).
- **How:** grep of headers/cpp (MaterialEditingLibrary, MaterialExpression*, PyGenUtil, CsvProfiler, ConfigCacheIni, GameEngine, GameUserSettings, Niagara, EnhancedInput, UMG, SlateCore), `ls`/`fc-query`/`strings` on content, read-only look at Game/Config, Game/Content and Saved/Logs/TwilightAssets.log.
- **Result:** 19 corrections, marked "CRITIC FIX:" in the reports; full list in docs/research/05_critic.md. Blockers: (1) CSV EndCapture().Wait() deadlocks on the game thread; (2) inline ';' ini comments corrupt +TargetedRHIs; (3) xdotool --name 'Twilight' never matches (window title is "Վահագն (… SF_VULKAN_SM6)"); (4) the composite font expected Roboto but Content/Fonts has NotoSans, so Armenian would render as boxes; (5) [SystemSettings] r.VSync overrides GameUserSettings VSync. materials_build.py: no functional error (it has already run with 0 errors); a verification header comment was added. Still unverified: HLSL compile, DMX user-param types, SM6 on Iris Xe.

## 2026-10-18 (գիշեր) — Քայլ 9. Վերանայում, ուղղումներ, Հայկ, Արալեզ, Հաբ
- **Workflow «vahagn-code-review»** (4 վերանայող + 17 ստուգող, 21 գործակալ). 13 հաստատված խնդիր, 1 մերժված։ Կարևորները՝ `bExecuteWhenPaused` (հավաքման սխալ → `UInputAction::bTriggerWhenPaused`), `NotifyHit(bool)`-ը թաքցնում էր `AActor::NotifyHit` (-Werror → `RegisterHit`), վիշապի հատվածների overlap-ի ծանրություն (→ `ECC_PhysicsBody` + block, fireball OnHit), avoidance trace-ը by object type, ակտիվների բացակայության քեշ, սլաքներ տեսախցիկի ետևում, gamepad Y/deltaTime, Nova/բոս dilation, միավորների tier։ Բոլորը կիրառված են։
- **Տառատեսակներ.** Noto Armenian-ում թվանշաններ/լատինատառեր չկան (`fc-query`) → composite font. Noto Sans/Serif (լատինական) + Noto Armenian (U+0530–058F, FB13–FB17)։
- **Ընդհանուր դասեր.** `ATwEnvironment` (երկինք/մառախուղ/post/երաժշտություն/կայծեր/terrain), `TwUi` (Slate գործիքներ)։
- **Հայկ** (HaykArcher, HaykArrow, HaykShield, HaykWorld, HaykGameMode+Preview, HaykPlayerController, HaykHud). հերթափոխով մենամարտ, քամի, հետագծի նախադիտում, ռոբոտի բալիստիկ լուծիչ (3 դժվարություն, «սովորում» է), եռաթև նետ (slow-mo + ղեկավարում), վահաններ, 2 խաղացող, գիշերային աշխարհ։
- **Արալեզ** (AralezWorld, AralezSpirit, AralezActors, AralezGame). պտուտակաձև թունել 3 գոտով, 4 Արալեզ (1 խաղացող + 3 ռոբոտ), հոգու լույսեր, Շամիրամի ստվերներ, պոռթկում/ոռնոց։
- **Հաբ** (TwHub). «ԾԻՐԱՆԻ» գլխավոր մենյու, 3 քարտ, Դիցարան (11 կերպար՝ հունական զուգահեռներով)։
- **Config.** map-prefix GameMode-ներ, GameDefaultMap=L_Menu, SM6+SM5, DefaultGameUserSettings.ini։
- **Workflow «games23-code-review»** գործարկված նոր կոդի համար։ Շարժիչի հավաքումը՝ ~1050/2694։

## 2026-10-18 21:40 — Chapter 2 «Hayk» + chapter 3 «Aralez» audio (audio subagent)
- **What:** 13 new mono SFX plus a stereo cave ambience, and 2 stereo music loops (`music_hayk`, 72 s; `music_aralez`, 72 s) in `art/audio/{sfx,music}`. The generator is `art/audio/src/gen_chapters23.py`, which reuses `dsp.py`, `gen_sfx.py` and `gen_music.py`. It is deterministic and needs no downloads.
- **How:** `cd art/audio/src && OMP_NUM_THREADS=1 nice -n 15 python3 gen_chapters23.py`. The SFX take about 10 s and the music about 2.5 min. Verify with `python3 gen_chapters23.py --verify` or `python3 analyze.py`.
- **Result:** ALL CHECKS PASSED. That means 48 kHz/16-bit, peaks at -1 dBFS or lower, 0 clipped samples, DC under 3e-4, exact durations and seamless loops. Music is at -14.0 LUFS, confirmed with ffmpeg ebur128. Details are in `art/audio/SETUP_LOG.md` steps 12–19 and the README table. Nothing under `Game/` was touched, and UE was not launched.

## 2026-10-18 (գիշեր) — Քայլ 10. Առաջին գործարկումներ, արագություն, տեսողական ուղղումներ
- **Շարժիչ.** UBT-ն վերակառուցեց 2694 action (77 րոպե, 10 զուգահեռ՝ RAM-ի սահմանափակում)։ Մոդուլը հավաքվեց 1 ուղղումից հետո (`*/` մեկնաբանության մեջ)։
- **Workflow «games23-code-review»** (20 գործակալ). 15 հաստատված խնդիր (unity-ում `using namespace` բախումներ → `bUseUnity=false`, `&&`/`||` փակագծեր, նետի ղեկ, pause-ի ժամանակ լարում, նետը ոսկորին, slow-mo վերականգնում, ինքնահարված, Արալեզի արդյունքների սառեցում, ռոբոտներ, պատի շառավիղ, կայծերի Z, SoulLight perf)։ Կիրառված են։
- **Ձայներ.** գործակալը ստեղծեց 15 նոր WAV (Հայկ, Արալեզ), ներմուծված են (ընդամենը 35)։
- **Առաջին run (Vahagn, autopilot).** ամբողջ ցիկլը աշխատում է (ալիքներ → բոս → հաղթանակ/պարտություն), HUD-ը և հայերեն տառատեսակները՝ ճիշտ։ Խնդիրներ՝ սպիտակ էկրան (ձեռքով էքսպոզիցիա 11.5 → 0, `-TwExposure=` override), 14 FPS։
- **Պրոֆիլավորում (CSV + `r.GPUCsvStatsEnabled`).** TSR-ը՝ 26 մվ GPU → `r.AntiAliasingMethod=2` (TAA). մարտում CPU-bound (render thread 12 մվ) → կրակե գնդակի պոչ 5→3, կյանք 4→2.4 վ, պայթյունների փոխարեն `ATwFlash` (1 պրիմիտիվ), շնչի FX throttling, վիշապի հատվածներ 26→21, փշեր 1/3։ GPU-ն throttling է անում «balanced» ռեժիմում → `powerprofilesctl set performance` (play.sh-ն նույնն է անում)։
- **Արդյունք.** Vahagn 300 վրկ թեստ՝ միջին 95 FPS, p99 67 FPS։ Հայկ՝ 80–88 FPS, Արալեզ՝ 114 FPS։
- **Հավասարակշռում.** վիշապների կյանքը ×2, բոսը 460, ալիքներ 4/5/6 → ավտոպիլոտը հաղթում է ~4.5 րոպեում։
- **Տեսողական.** երակների/ճաքերի sharpness (noise≈0.5 ամբողջ մակերեսը լուսավորում էր), hit flash-ի նվազեցում, վիշապի մարմնի հեռավորություն ըստ շառավղի, մենյուում հերոսը աջ կողմում, gradient վնասի vignette, Հայկ՝ մենամարտի հեռավորություն 76→54 մ, FOV 52, լավ զինվորներ, ռոբոտի ճշգրտություն, Արալեզ՝ փետրավոր թևեր, մուգ ստվերներ, երկար թունել, `M_Additive`-ին ISM usage (սև գնդերի պատճառը)։
- **Գործիքներ.** `Tools/run_test.sh` (տեսագրում + կադրեր), `Tools/perf_probe.sh`, `Tools/shot.sh`, `TwTestHarness` (Hayk/Aralez autoplay)։

## 2026-10-18 (գիշեր) — Քայլ 11. Իսկական կառավարման թեստեր, հավասարակշռում, ռեգրեսիա
- **xdotool-ով իսկական մկնիկ/ստեղնաշար** (`Tools/click_play.sh`, `input_test.sh`). մենյուի կոճակներ, հաբ → Դիցարան → Հայկ, Հայկի կրակոց, Արալեզի թռիչք/ոռնոց՝ աշխատում են։
- **Գտնված բագ.** նոր խաղացողը մահանում էր ~10 վրկ-ում (4 վիշապ միաժամանակ կրակե շունչ). ուղղում՝ հարձակման «tokens» (առաջին ալիքում 1, հետո 2), առաջին հարձակումից առաջ 5–8 վրկ, շնչի վնասը 3→1.6/tick, Normal վնաս ×0.8, վերականգնում 6/վ 3 վրկ հետո։ Պասիվ խաղացողը հիմա գոյատևում է 90+ վրկ։
- **Այլ ուղղումներ.** երկար վերնագիրը (Խորենացու տողը) տեղավորվում է, մենյուում Վահագնը աջ կողմում, Հայկ՝ թշնամու նշիչ, Արալեզ՝ մեղմ ոռնոցի ալիք, «−» → «-», «✦» → «·», կրակե հետք, տեսախցիկի ցնցում։
- **Ռեգրեսիա.** վթար չկա։ Առաջին չափումը ցածր էր ֆոնում մոռացված Unreal պրոցեսի պատճառով. այն փակելուց հետո՝ Vahagn 105 FPS (p99 76), Hayk 88, Aralez 100։
- **Փաստաթղթեր.** `docs/HOW_TO_PLAY_hy.md`, `Tools/play.sh` (լռելյայն՝ հաբ), `Tools/Twilight.desktop`։

## 2026-10-19 00:40 — Քայլ 12. Դիզայնի քննադատություն և տեսողական մաքրում (երեք խաղ)
- **Design-critique workflow** (commit `538602c`). 24 կետ. վիշապի մահվան շղթա և օբսիդիանի մաշկ, տեսանելի կրակե շունչ, առանց ծխի պայթյուններ, ծննդի տեսախցիկ, Հայկի վահաններ/թագ/սաղավարտ, վրիպման կադրավորում, սպանության climax, Արալեզի ավարտի էկրան, բյուրեղներ, ստվերներ, տեքստի եզրագծեր։
- **Կրակե շունչ** (`Vishap.cpp`). ինտենսիվությունը 0.45, տեսախցիկից հեռավորությամբ մարում. այլևս չի ծածկում էկրանը։ **FireOrb**-ը նույնպես մարում է ոսպնյակի մոտ (commit `29daa68`)։
- **Ծով** (`Tools/materials_build.py` → `M_Water_Purple`). StarterContent-ի `T_Water_N`-ի բջիջները բարձրությունից «կետավոր նախշ» էին տալիս, իսկ արևի փայլը՝ կետավոր։ Փոխարինված է 8 վերլուծական ալիքով (ճշգրիտ cos թեքություններ), որոնց փուլը շեղվում է Perlin noise-ով (domain warp), և հեռավորությամբ մարում կա (`NormalFadeDistance`)։ Վերակառուցում՝ `TW_ONLY=materials UnrealEditor-Cmd TwilightAssets.uproject -run=pythonscript -script=Tools/build_assets.py` → 7 նյութ, 0 սխալ (`docs/logs/build_assets_4.log`, `Saved/Logs/TwilightAssets.log`)։ Արդյունք՝ իսկական ջրի տեսք, արևի ճանապարհին փայլատակումներ։
- **Կրակե գնդեր** (`Fireball.cpp`). Մեծ/թշնամական գնդերը intensity 25-ից tonemap-ով սպիտակ սկավառակ էին դառնում. հիմա հագեցած թաղանթ է (intensity 5–7, Falloff 3) և ներսում տաք միջուկ (`InnerCore`)։ Թշնամու գնդերը կարմիր են, խաղացողինը՝ ոսկեգույն։
- **Բռնկումներ** (`TwFlash`, `TwFx::Burst`). peak intensity 20 → 5, Falloff 3, տեսախցիկի մոտ մարում, հագեցած գույներ. վիշապի մահը և հարվածներն այլևս կրեմագույն ամպեր չեն։ **FireOrb**-ը ոսկե կայծ է (intensity 6)։
- **Արալեզի ավարտ** (`AralezWorld.cpp`, `AralezGame.cpp`). Վերջին հատվածում (T>0.9) կարմիր մառախուղն անցնում է բարակ ոսկե մշուշի (density → 0.004)։ Դարպասի միջուկը ոսկե թաղանթ է տաք սրտով։ Թունելի վերջը փակված է ժայռով (դատարկություն չի երևում)։ Արդյունքների համար կա առանձին `ACameraActor`, որը նայում է դարպասին և դանդաղ մոտենում (`StartEndCamera`/`TickEndCamera`)։ Հոգու լույս վերցնելու բռնկումը (1.5 մ կրեմագույն գունդ) փոքրացված է, իսկ ռոբոտների ժապավեն-հետքերը բարակում են ոսպնյակի մոտ։
- **Ռեգրեսիա** (`Tools/run_test.sh`).
  - Vahagn 300 վ, god pilot՝ ՀԱՂԹԱՆԱԿ 248 վ-ում, 99.8 FPS (p99 68.5)։
  - Hayk 200 վ՝ հաղթանակ + երկրորդ մենամարտ, 83.8 FPS։
  - Aralez 185 վ՝ ավարտ (1-ին/3-րդ/4-րդ տեղ տարբեր run-երում), 94–109 FPS։
  - Սխալներ/վթարներ չկան։

## 2026-10-19 01:00 — Քայլ 13. Երկրորդ աշխարհներ (փոթորիկ, գիշեր) և Shipping փաթեթ
- **Վահագն. փոթորկի աշխարհ** (`VahagnWorld::SetStorm/ApplyStorm/StrikeLightning/UpdateBolt`)։ Մեծ վիշապի հայտնվելու պահին ~6 վրկ-ում փոխվում են արևը, SkyAtmosphere-ի luminance-ը (բոսորագույն), Mie մշուշը, մառախուղը, sky light-ը (երկու անգամ վերանկարվում է) և ծովի գույները (`SeaMat`)։ Ամեն 3.5–8 վրկ-ը մեկ կայծակ է խփում. 11 ատամնավոր հատված և 2 ճյուղ (18 cylinder-ի pool), թարթում, մանուշակագույն բռնկում Moon լույսով (+6), ջրի ցայտք և ուշացած ամպրոպ (`sfx_big_explosion` pitch 0.42)։ `StartMatch`-ը փոթորիկն անջատում է։ Փորձարկման դրոշ՝ `-TwBossTest` (ալիքները բաց է թողնում)։ Առաջին տարբերակում Rayleigh-ի իջեցումը վերին երկինքը սև էր դարձնում, ուստի այն պահպանվեց, իսկ գույնը տրվում է luminance factor-ով (1.6, 0.42, 0.55)։ Կայծակի flash-ը 18-ից իջեցվեց 6-ի, որովհետև կղզիները սպիտակում էին։
- **Ծովի warp**։ Կայծակի լույսի տակ ալիքների ինտերֆերենցիան կանոնավոր կետեր էր տալիս։ Warp-ի հաճախականությունը 0.13-ից բարձրացվեց. 0.37 արժեքը մարմարյա տեսք տվեց, ուստի վերջնականը 0.2 է (WarpAmount 1.0)։
- **Գիշերային երկինք** (`ATwEnvironment::BuildNightSky`, `FTwSkyPreset::SkyLuminance/Stars/bMoonDisc`)։ Հայկի գիշերը լուսավոր կապույտ «ցերեկ» էր (լուսինը SkyAtmosphere-ի համար արև է 28°-ում)։ Հիմա luminance-ը 0.035/0.045/0.12 է, կա 1400 աստղ 3 կմ գմբեթի վրա (ISM), լուսնի սկավառակ, ավելի մուգ մառախուղ և sky light, իսկ լուսնի լույսը պակաս հագեցած է։ Արդյունք՝ լուսնային գիշեր, աստղեր և Բելի բանակի տաք ջահեր։
- **Հայկ**։ Հարվածի flash-ը կարմիր է (`FlashColor` 1/0.22/0.04, ×0.45)։ Հաբի քարտի ենթավերնագիրը կտրված էր, փոխվեց «Աղեղի մենամարտ · 1–2 խաղացող»։
- **Shipping փաթեթ, փորձ 2** (`docs/logs/package2.log`)։ Շարժիչի Shipping մոդուլները հավաքվեցին 946/948 (21 րոպե, UBA)։ Ձախողում՝ `TwEnvironment.h` UHT mismatch, քանի որ header-ը խմբագրվել էր հավաքման ընթացքում։ Դաս. փաթեթավորման ժամանակ կոդ չխմբագրել։ Editor-ը զուգահեռ հավաքվում էր `-NoMutex`-ով։
- **Փորձ 3**-ը գործարկված է (`docs/logs/package3.log`)։

## 2026-10-19 02:00 — Քայլ 14. Shipping փաթեթ. փորձարկում և ուղղումներ
- **Փաթեթ** (`RunUAT BuildCookRun ... -clientconfig=Shipping -build -cook -stage -pak -iostore -archive -archivedirectory=Build -nocompileeditor`)։ Փորձ 3-ը հաջողվեց (14.5 րոպե), հետագա incremental-ները տևում են 1–2 րոպե (`docs/logs/package3..7.log`)։ Արդյունք՝ `Build/Linux/Twilight.sh`, 1.7 ԳԲ։
- **Բագ 1. վարորդի modal պատուհան։** Shipping-ը ցույց էր տալիս «WARNING: Known issues with graphics driver» (Intel Iris Xe 25.2.8-ը deny-list-ում է, `DynamicRHI.cpp:233`)։ Ուղղում՝ `DefaultEngine.ini [SystemSettings] r.WarnOfBadDrivers=0`։ Ստուգված է առանց `-unattended`-ի. պատուհան չկա։
- **Բագ 2. հրամանային տողի քարտեզն անտեսվում է։** `UGameInstance::StartGameInstance`-ը Shipping-ում քարտեզը զրոյացնում է (`UE_ALLOW_MAP_OVERRIDE_IN_SHIPPING`)։ Ուղղում՝ `ATwHubController::BeginPlay`-ը կարդում է `-TwMap=L_X` և մեկ անգամ բացում գլուխը (static flag, որպեսզի մենյու վերադառնալիս չկրկնվի)։ `play.sh`-ն այժմ գործարկում է փաթեթը `-TwMap=$MAP`-ով։
- **Բագ 3. փաթեթում 37 FPS։** Editor-ի `Saved/Config/.../GameUserSettings.ini`-ում `sg.Shadow/Reflection/PostProcess/EffectsQuality=0` էր, իսկ փաթեթը վերցնում էր `DefaultGameUserSettings.ini`-ի 2-երը։ Ուղղում՝ defaults-ը համապատասխանեցվեց (0)։ Արդյունք՝ փաթեթ Vahagn 104.4 FPS (p95 78.8, p99 70.7), Hayk 90.7, Aralez 103.8։
- **Ծովի կետեր (վերջնական պատճառ)։** Warp-ը նմուշառում էր StarterContent-ի Perlin տեքստուրան, որի բծերը փուլը շեղում էին ու բարձրությունից կանոնավոր կետեր տալիս։ Ուղղում՝ առանց տեքստուրաների վերլուծական warp (3 երկար sine), երկար ալիքներին ամենամեծ warp, հավասարեցված կշիռներ։ Ծովի հարթությունը 5-ից 40 կմ է, որ բարձրությունից եզրը չերևա։ Արդյունք՝ մաքուր, բնական ալիքներ (`docs/capture/1019_013420`)։
- **Արալեզ.** ռոբոտ-ոգին ոսպնյակի մոտ (<3.2 մ) թաքնվում է։
- **Իսկական գործարկման թեստ.** `Tools/play.sh` (ամբողջ էկրան 1920×1200) → հաբ → Հայկ → «ԸՆԴԴԵՄ ԲԵԼԻ» → աղեղի լարում/կրակոց xdotool-ով → նետի տեսախցիկ → Բելի հերթ։ Ամեն ինչ աշխատում է։
- **Գործիք.** `Game/Tools/pkg_test.sh <L_Map> <sec>`՝ փաթեթի autoplay թեստ (summary-ն՝ `~/.config/Epic/Twilight/Saved/TwTestSummary.txt`)։

## 2026-10-19 02:10 — Քայլ 15. Chaos թեստեր և ձայն
- **`Game/Tools/chaos_test.sh <map> <sec> [seed]`** (`START="x y"`՝ գլխի առաջին կոճակը)։ Փաթեթի վրա պատահական իսկական մուտք է տալիս (մկնիկ, ձախ/աջ կոճակներ, WASD, Space, Ctrl, Shift, Q, Esc) և 3 վրկ-ը մեկ կադր պահում։
  - Vahagn 150 վ՝ դադար/մենյու/հաբ անցումները ճիշտ են (փակումը եղավ պատահական «ԵԼՔ» սեղմումից, ոչ թե վթարից)։
  - Hayk 150 վ և Aralez 150 վ՝ կենդանի են, կախվածություն չկա։
- **Ձայն փաթեթում.** Sink monitor-ից ձայնագրված է `pw-record -P '{ stream.capture.sink=true }' --target 58`-ով։ Խիտ մարտում գումարը կտրվում էր (381 clipped sample, պիկ 1.0)։ Ուղղում՝ `ATwEnvironment::BeginPlay`-ում `SetTransientPrimaryVolume(0.7)`։ Արդյունք՝ 0 clipped, RMS −16 dB, պիկ ≤ 0.9։
- Ուշադրություն. համակարգի ձայնը (Built-in Audio) 10% է. ներկայացման ժամանակ բարձրացնել։

## 2026-10-19 02:45 — Քայլ 16. Քննադատության երկրորդ փուլ (workflow «twilight-critique-2») և ուղղումներ
- **Workflow.** 3 քննադատ գործակալ (մեկը՝ ամեն խաղի համար) կարդացին փաթեթի կադրերը (`docs/capture/critique2/`) և աղբյուրը։ Արդյունքը՝ 23 կոնկրետ դիտողություն։ Իրականացված են.
- **Վահագն**
  - Տեսախցիկ. `CameraLagSpeed` 9→14, `LagMaxDistance` 320→120 (հերոսը չի «փախչում» էկրանի եզր)։ Վիշապի հատվածները ոսպնյակի մոտ թաքնվում են (`Vishap::UpdateBody`)։
  - Կեցվածք. «ջրի վրա կանգնած բռնցքամարտիկի» տեսքը շտկված է։ `UTwPoseAnimInstance::SetOneShotMask("spine_01")`-ով կրակոցի անիմացիան միայն վերին մարմնի վրա է, իսկ ոտքերը թռչում են։ Թեքությունը միշտ ≥20°, hover rate-ը՝ 0.35։
  - Արևի պոռթկում (Q). հերոսի վրա BigExplosion-ը հանված է (էկրանը կրակով էր լցնում)։ Nova-ն 3, պայթյուններ՝ խոցված վիշապների վրա (≤6)։ Պատրաստ լինելիս 4 վրկ կենտրոնական հուշում և օղակ նշանառության շուրջ։
  - HUD. թշնամու սլաքները էլիպսի վրա են (ժամաչափի/գոտիների տակով), կրկնվողները միավորված են։ Ենթավերնագիրը չափված վերնագրի տակ է։
  - Վիշապ. ավելի մուգ օբսիդիան (vein sharpness 45), սառը եզր (0.3/0.5/1.0 × 0.45), մեծ աչքեր, երկար եղջյուրներ։ Կրակե շնչի կոնը ոսպնյակի մոտ ավելի է մարում (min 0.05)։
  - Վիշապաքարեր. առանցքներն ուղղված են (X = խորություն), այնպես որ փորագրությունները հիմա երևում են երկու կողմից։
  - Հայերեն. «վիշապն ավելի», «Ծովն եռում», «Արալեզն իջնում», «ստվերներն ավելի», «ժառանգներն ազատ», «Բելն այս… Կրկին փորձի՛ր», «1-ին/2-ՐԴ», «Մասիսի ստորոտ» (գիշերային intro)։ Արալեզի «►» glyph-ը (tofu) փոխարինվեց «»»-ով։
- **Հայկ**
  - **Իսկական բագ.** Rifle `MM_HitReact_*` անիմացիաները additive են, իսկ մենք դրանք blend էինք անում որպես լրիվ պոզ, ու կմախքը փլվում էր. Բելն ամեն հարվածից «անհետանում» էր (կուրծքը 996→767, գլուխը կրծքից ցածր)։ Հրավառությունը թաքցնում էր սա։ Ուղղում՝ `FTwPoseProxy::Evaluate`-ում `IsValidAdditive()` → `AccumulateAdditivePose`։ Ստուգված է debug log-ով (կուրծք ≈994, գլուխ ≈1054)։
  - Տեսախցիկ. հերթափոխը կտրուկ cut է (`bCamCut`), լարման zoom FOV 52→34 է, Բելի հերթի կադրը լայն ու ցածր է, հարվածի կադրը՝ ամբողջ մարմինը (terrain clamp), իսկ վրիպումը կադրավորվում է թիրախի հետ (1600 սմ clamp)։
  - Վրիպման ուղղություն. «{0} մ-ով անցավ / չհասավ / կողքով»։ Banner-ը ստորին երրորդում է, վնասը՝ կարմիր մեծ թվով։ Հակառակորդի նշիչը երևում է նաև Բելի հերթին։
  - Հարված. սովորական հարվածին՝ կայծեր, մեծ կրակ՝ միայն եռաթև նետին կամ սպանությանը։
- **Արալեզ**
  - Պատ. սահմանափակումը `WallRadius(T, angle) - 260` է (ոգին այլևս չի մտնում ժայռի մեջ)։ Տեսախցիկը պատին մոտ boom-ը կարճացնում է մինչև 260։
  - Ռոբոտներ. թաքնվում են ոսպնյակից 4.5 մ-ի վրա, խաղացողից հեռու են պահում (1000)։ Հետքերն ավելի կարճ ու բարակ են (0.6 վրկ, quadratic taper)։
  - **Ստորերկրյա գետ.** գոտի 1-ում ջրի շերտ է (`BuildRiver`, procedural strip, մուգ teal `M_Water_Purple` MID, RippleSpeed 0.5)։ Ոգիները սահում են ջրի վրայով (clamp)։ Առաջին տարբերակում winding-ը հակառակ էր, ու ջուրը չէր երևում։
  - Ստվերներ (wraith). սև թիկնոց, մուգ բոսոր եզր, աուրա, մասշտաբ 1.4, թաքնվում են ոսպնյակի մոտ։ Առաջին տարբերակը +2.2 exposure-ի պատճառով վարդագույն էր։
  - Ավարտ. finish cinematic-ը 1.3 վրկ է (~3.7 իրական), end camera-ն նայում է դարպասից ցածր։ Banner-ի ենթավերնագիրը չափված է։

## 2026-10-19 03:10 — Քայլ 17. Վերջնական փաթեթ և ստուգում
- Հաղթանակից հետո փոթորիկը մարում է (`EndMatch` → `SetStorm(false)`). ծովը վերադառնում է մանուշակագույն մայրամուտին։
- Փաթեթը վերակառուցվեց (`docs/logs/package9.log`, EXIT=0)։
- **Փաթեթի autoplay** (`Tools/pkg_test.sh`).
  - Վահագն 290 վ՝ ՀԱՂԹԱՆԱԿ 4:03-ում, 112.2 FPS (p95 83, p99 75)։
  - Հայկ 150 վ՝ 88.6 FPS։
  - Արալեզ 185 վ՝ 1-ին տեղ, 104.9 FPS։
- **Chaos** (`Tools/chaos_test.sh`, ամեն խաղը 120 վ, նոր seed-եր)՝ երեքն էլ կենդանի են։
- Commit `8a2fed0` (+ փաստաթղթեր)։
