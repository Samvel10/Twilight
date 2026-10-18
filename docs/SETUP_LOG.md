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
