# 04 — Automated testing, performance tuning and capture on Linux (UE 5.8.2, Intel Iris Xe, Vulkan)

Research date: 2026-10-18. Engine: `/home/samo/UnrealEngine-5.8` (source build). Project: `/var/www/html/Twilight/Game/Twilight.uproject` (only read, never changed by this research).
Paths below that start with `Runtime/` are relative to `/home/samo/UnrealEngine-5.8/Engine/Source/`. A claim tagged **VERIFIED** was read in the 5.8 source or checked on this machine. A claim tagged **UNVERIFIED** comes from general knowledge or an estimate.

---

## 0. Machine facts (checked read-only on this laptop)

| Item | Value | How it was checked |
|---|---|---|
| Session | **X11** (`XDG_SESSION_TYPE=x11`, `DISPLAY=:0`, GNOME) | `echo` |
| Screen | 1920x1200 @ 60.01 Hz | `xrandr` |
| GPU | Intel Iris Xe (Raptor Lake-P), Mesa 25.2.8 ANV, Vulkan 1.4.318 | `vulkaninfo --summary` |
| Second Vulkan device | `llvmpipe` (CPU). UE **skips CPU devices** unless `-AllowCPUDevices` is passed, so it cannot select it by mistake: `Runtime/VulkanRHI/Private/VulkanRHI.cpp:257-260` | VERIFIED |
| Features that matter for SM6 | shaderInt64, shaderImageInt64Atomics, shaderBufferInt64Atomics, subgroupSizeControl, descriptor indexing: all `true` | `vulkaninfo` |
| CPU / RAM | i7-13700H (20 threads), 30 GB | `/proc/cpuinfo`, `free` |
| iGPU clock | min 100 MHz, max/RP0 1500 MHz | `/sys/class/drm/card1/gt_*` |
| Power profile | **balanced**, AC connected | `powerprofilesctl get` |
| Tools | `ffmpeg` 7.0.2 static (`~/.local/bin/ffmpeg`; x11grab yes, libx264 yes, **no VAAPI, no Pulse**), `xdotool`, `xwininfo`, `wmctrl`, `scrot`. **`ffprobe` is not installed.** | `which`, `ffmpeg -devices/-encoders` |
| x11grab test | 2-second capture plus frame extraction worked | ran in the scratchpad, then deleted |
| Existing caches | Zen DDC at `~/.config/Epic/UnrealEngine/Common/Zen/Data` (421 MB), Mesa shader cache at `~/.cache/mesa_shader_cache` (115 MB) | `du` |
| Game target builds | **None yet.** Only `UnrealEditor` and `ShaderCompileWorker` exist in `Engine/Intermediate/Build/Linux/` | `ls` |

**Before every test and before the presentation, do this:**
```bash
powerprofilesctl set performance      # balanced caps the iGPU clocks and power budget
```
Keep the laptop on AC. Iris Xe performance depends heavily on the package power limit (UNVERIFIED magnitude, commonly 10–25 %).

---

## 1. Launching the game non-interactively

### 1.1 Base command (editor binary, `-game`, uncooked content)

```bash
UE=/home/samo/UnrealEngine-5.8/Engine/Binaries/Linux/UnrealEditor
P=/var/www/html/Twilight/Game/Twilight.uproject
"$UE" "$P" /Game/Twilight/Maps/L_Vahagn -game -windowed -ResX=1600 -ResY=900 -WinX=160 -WinY=150 \
     -nosplash -unattended -NOSCREENMESSAGES -stdout -FullStdOutLogOutput \
     -seconds=120 \
     -ExecCmds="r.VSync 0, t.MaxFPS 0, stat fps, stat unit" \
     > /tmp/twilight_run.log 2>&1
```

Every flag below was checked in the engine source:

| Flag | Effect | Source (5.8) |
|---|---|---|
| `-game` | Runs the game, not the editor UI | standard |
| `<map>` | Map to load at start | standard |
| `-windowed` | Windowed mode | `Runtime/Engine/Private/GameEngine.cpp:291` |
| `-fullscreen` | Fullscreen mode | `GameEngine.cpp:296` |
| `-ResX= -ResY=` | Window size | `GameEngine.cpp:326-327` |
| `-ForceRes` | Uses the resolution even if the monitor does not support it | `GameEngine.cpp:414` |
| `-WinX= -WinY=` | Window position (needed for fixed-region capture) | `GameEngine.cpp:565-567` |
| `-nosplash` | No splash on Linux | `Runtime/ApplicationCore/Private/Linux/LinuxPlatformSplash.cpp:687` |
| `-unattended` | `FApp::IsUnattended()`: no blocking dialogs or crash-reporter UI | `Runtime/Core/Private/Misc/App.cpp:278`, `Core/Private/Unix/UnixPlatformCrashContext.cpp:649` |
| `-nosound` | Disables audio (unless `-enablesound` is also passed) | `Runtime/Core/Public/Misc/App.h:436` |
| `-NOSCREENMESSAGES` | Hides on-screen debug messages | `Runtime/Launch/Private/LaunchEngineLoop.cpp:4313` |
| `-statunit` | Runs `stat unit` at startup | `LaunchEngineLoop.cpp:4318-4320` |
| `-stdout`, `-FullStdOutLogOutput`, `-AllowStdOutLogVerbosity` | Copies the log to the terminal | `Core/Private/HAL/FeedbackContextAnsi.cpp:27`, `Core/Private/Misc/OutputDeviceStdOut.cpp:190-195` |
| `-LOG=name.log` / `-ABSLOG=/abs/path.log` | Log file name or path. The default is `<Project>/Saved/Logs/Twilight.log` | `Core/Private/GenericPlatform/GenericPlatformOutputDevices.cpp:84-87` |
| `-ExecCmds="a, b, c"` | Console commands separated by commas, **all run on the first engine tick** with no delay. A single quote `'` becomes `"` so arguments can contain commas. **Not in Shipping.** | `Runtime/Engine/Private/UnrealEngine.cpp:2540-2552` (`#if !(UE_BUILD_SHIPPING)`), `Runtime/Engine/Private/ParseExecCommands.cpp:11-77` |
| `-EXEC=file.txt` | Runs a console-command file | `UnrealEngine.cpp:2544-2547` |
| `-vsync` / `-novsync` | Sets `r.vsync 1/0` | `UnrealEngine.cpp:2555-2561` |
| **`-seconds=N`** | **Auto-quit after N seconds of accumulated game delta time**, counted from frame 6. Works without `-benchmark`. **Not in Shipping.** | `LaunchEngineLoop.cpp:4708-4710` (parse), `:5692-5696` (`RequestExit`), `:6073-6076` (accumulate) |
| `-benchmark` | `FApp::SetBenchmarking`. **It forces a fixed time step** (`UnrealEngine.cpp:3005`), detaches INI writes (`LaunchEngineLoop.cpp:4324`) and fixes the random seed (`:2462`). **Do not use it to measure real FPS**, because the game then advances by a fixed delta and does not run in real time. | `LaunchEngineLoop.cpp:2451` |
| `-BENCHMARKSECONDS=N` | Same as `-seconds`, only with `-benchmark` | `LaunchEngineLoop.cpp:4717-4722` |
| `-FPS=N` | Sets the fixed delta to 1/N (for `-benchmark`/`-UseFixedTimeStep`) | `LaunchEngineLoop.cpp:4726-4731` |
| `-UseFixedTimeStep`, `-Deterministic` (= fixed step + fixed seed), `-FixedSeed` | Deterministic simulation. Useful for reproducible gameplay bots, not for FPS numbers. | `LaunchEngineLoop.cpp:2457-2462` |
| `-sm5` / `-sm6` / `-es31` | Forces the Vulkan feature level | `Runtime/RHI/Private/Linux/LinuxDynamicRHI.cpp:18-30` |
| `-vulkan` / `-opengl` | Forces the RHI | `LinuxDynamicRHI.cpp:48-53` |
| `-ini:Engine:[Section]:key=value` | Overrides any INI value from the command line (A/B tests without editing files) | `Runtime/Core/Private/Misc/ConfigCacheIni.cpp:1718` |
| `-DPCVars=r.X=1,r.Y=2` | Sets cvars at device-profile priority | `Runtime/Engine/Private/DeviceProfiles/DeviceProfileManager.cpp:739` |
| `-clearPSODriverCache` / `-ClearVulkanBinaryProgramCache` | Deletes the Vulkan PSO disk cache (use it to test a cold start) | `Runtime/VulkanRHI/Private/VulkanPipeline.cpp:546` (comment and logic) |
| `-logPSO` | Records PSOs to `Saved/CollectedPSOs/` | `Runtime/RHI/Private/PipelineFileCache.cpp:2290, 3116` |

**Gotchas**
* The editor binary with `-game` reads its config and writes its output under the **`LinuxEditor`** platform name. A packaged game uses **`Linux`**. `FPlatformProperties::PlatformName()` returns `"LinuxEditor"` when `HAS_EDITOR_DATA` (`Runtime/Core/Public/Linux/LinuxPlatformProperties.h:58-68`). Screenshots therefore go to `Saved/Screenshots/LinuxEditor/` and saved user config to `Saved/Config/LinuxEditor/` (`Runtime/Core/Private/Misc/Paths.cpp:553-556`, `Misc/ConfigContext.cpp:84-89`).
* Because `-ExecCmds` runs everything on the first tick, a "quit after 60 s" cannot be written in ExecCmds alone. Use `-seconds=`, `CsvProfile EXITONCOMPLETION` (section 2) or the C++ hook (1.2).
* In **Shipping**, `-ExecCmds`, `-seconds`, `-benchmark` and the CSV profiler are all compiled out (`CSV_PROFILER_ALLOW_DEBUG_FEATURES = !UE_BUILD_SHIPPING`: `Runtime/Core/Public/ProfilingDebugging/CsvProfilerConfig.h:16`, `CSV_PROFILER_ENABLE_IN_SHIPPING 0`: `:10`). **Run all automated tests on Development.** The C++ hook below can be kept in Development only (`#if !UE_BUILD_SHIPPING`).

### 1.2 Recommended: a test hook in the game itself (`-AutoPlayTest=SECONDS`)

Nobody can press keys during the night test, so the game should be able to play itself. The main agent owns the code; this is a drop-in proposal. Every API it uses was checked:

* `FParse::Value/Param`, `FCommandLine::Get()`: standard Core API.
* `FCsvProfiler::Get()->BeginCapture(int, const FString& Folder, const FString& File, ECsvProfilerFlags)` and `EndCapture()` returning `TSharedFuture<FString>`: `Runtime/Core/Public/ProfilingDebugging/CsvProfiler.h:422, 519-529`. `CSV_EVENT_GLOBAL(fmt, ...)`: `:60`. `FCsvProfiler::SetMetadata`: `:457`.
* `FScreenshotRequest::RequestScreenshot(const FString& InFilename, bool bInShowUI, bool bAddFilenameSuffix, bool bHdr=false, ...)`: `Runtime/Engine/Public/UnrealClient.h:219`.
* `FPlatformMisc::RequestExit(bool Force, const TCHAR* CallSite)`: `Runtime/Core/Public/GenericPlatform/GenericPlatformMisc.h:1086`.

```cpp
// TwilightAutoTest.h  (UGameInstanceSubsystem, so it lives across map loads)
#pragma once
#include "Subsystems/GameInstanceSubsystem.h"
#include "Tickable.h"
#include "TwilightAutoTest.generated.h"

UCLASS()
class UTwilightAutoTest : public UGameInstanceSubsystem, public FTickableGameObject
{
    GENERATED_BODY()
public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    // FTickableGameObject
    virtual void Tick(float DeltaTime) override;
    virtual TStatId GetStatId() const override { RETURN_QUICK_DECLARE_CYCLE_STAT(UTwilightAutoTest, STATGROUP_Tickables); }
    virtual bool IsTickable() const override { return bActive; }
    virtual bool IsTickableWhenPaused() const override { return true; }

    /** Gameplay code polls this: when true, the player pawn flies and fires on its own. */
    UFUNCTION(BlueprintPure) bool IsAutoPilot() const { return bActive; }
    bool IsGodMode() const { return bGod; }

private:
    bool  bActive = false, bGod = false, bCsvStarted = false, bExitRequested = false;
    float Duration = 0.f, Warmup = 10.f, ShotEvery = 15.f, Elapsed = 0.f, NextShot = 0.f;
    int32 ShotIdx = 0;
};
```

```cpp
// TwilightAutoTest.cpp
#include "TwilightAutoTest.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "UnrealClient.h"                       // FScreenshotRequest
#include "ProfilingDebugging/CsvProfiler.h"
#include "HAL/PlatformMisc.h"

void UTwilightAutoTest::Initialize(FSubsystemCollectionBase& C)
{
    Super::Initialize(C);
#if !UE_BUILD_SHIPPING
    const TCHAR* Cmd = FCommandLine::Get();
    bActive = FParse::Value(Cmd, TEXT("AutoPlayTest="), Duration) && Duration > 0.f;
    bGod    = FParse::Param(Cmd, TEXT("AutoGod"));            // the player cannot die (to see the boss)
    FParse::Value(Cmd, TEXT("AutoWarmup="), Warmup);          // skip shader/PSO hitches at start
    FParse::Value(Cmd, TEXT("AutoShotEvery="), ShotEvery);
    NextShot = Warmup;
    if (bActive) UE_LOG(LogTemp, Display, TEXT("[AutoTest] %.0fs, warmup %.0fs, god=%d"), Duration, Warmup, bGod);
#endif
}

void UTwilightAutoTest::Tick(float Dt)
{
#if !UE_BUILD_SHIPPING
    Elapsed += Dt;
#if CSV_PROFILER
    if (!bCsvStarted && Elapsed >= Warmup)
    {
        bCsvStarted = true;
        FCsvProfiler::SetMetadata(TEXT("Test"), TEXT("AutoPlay"));
        FCsvProfiler::Get()->BeginCapture(-1, FPaths::ProfilingDir() / TEXT("CSV"), TEXT("AutoPlay.csv"));
    }
#endif
    if (ShotEvery > 0.f && Elapsed >= NextShot)
    {
        NextShot += ShotEvery;
        const FString File = FPaths::ScreenShotDir() / FString::Printf(TEXT("auto_%03d.png"), ShotIdx++);
        FScreenshotRequest::RequestScreenshot(File, /*bShowUI*/true, /*bAddFilenameSuffix*/false);
#if CSV_PROFILER
        CSV_EVENT_GLOBAL(TEXT("Shot %d"), ShotIdx - 1);
#endif
    }
    if (!bExitRequested && Elapsed >= Warmup + Duration)
    {
        bExitRequested = true;
#if CSV_PROFILER
        if (FCsvProfiler::IsCapturing())
        {
            FCsvProfiler::Get()->EndCapture().Wait();          // blocks until the file is written
        }
#endif
        UE_LOG(LogTemp, Display, TEXT("[AutoTest] done after %.1fs"), Elapsed);
        FPlatformMisc::RequestExit(false, TEXT("TwilightAutoTest"));
    }
#endif
}
```
*Call `EndCapture()` from the game thread. Blocking on `.Wait()` should work because the processing thread writes the file (`CsvProfiler.cpp:4223-4270`). If it ever hangs, use the alternative `GEngine->Exec(nullptr, TEXT("CsvProfile EXITONCOMPLETION")); GEngine->Exec(nullptr, TEXT("CsvProfile STOP"));`, which exits only after the file is written (`CsvProfiler.cpp:4309-4313`). The `.Wait()` path is UNVERIFIED at runtime.*

Autopilot logic in the pawn or controller (gameplay code): `if (AutoTest->IsAutoPilot())` steer toward the nearest vishap or boss with a slight weave, fire the primary every 0.3 s and the special every 8 s, and do a dodge roll every 5 s. All stages (waves, then the boss, then victory) and every VFX then get exercised and recorded. With `-AutoGod` the run reaches the boss.

Run:
```bash
"$UE" "$P" /Game/Twilight/Maps/L_Vahagn -game -windowed -ResX=1600 -ResY=900 -WinX=160 -WinY=150 \
  -nosplash -unattended -NOSCREENMESSAGES -AutoPlayTest=480 -AutoGod -AutoWarmup=10 -AutoShotEvery=20 \
  -ExecCmds="r.VSync 0, t.MaxFPS 0"
```

### 1.3 Driving real input from outside (xdotool, X11)
X11 is confirmed, so `xdotool` can send synthetic keys and mouse events to the game window. This tests the real input path, not only the autopilot:
```bash
WID=$(xdotool search --sync --onlyvisible --name 'Twilight' | head -1)   # window title contains the project name (exact title UNVERIFIED)
xdotool windowactivate --sync "$WID"
xdotool keydown w; sleep 3; xdotool keyup w                 # fly forward for 3 s
xdotool mousemove_relative --sync -- 200 0                   # turn the camera
xdotool click 1                                              # fire
xdotool key space                                            # dash or jump
```
UNVERIFIED: whether UE's SDL relative-mouse mode accepts XTest relative motion. Keys and clicks normally work.

---

## 2. Measuring FPS: a verified recipe that writes average FPS and percentiles to a file

### 2.1 Option A (recommended): CSV profiler, no C++ needed
Facts from the source:
* Console command `CsvProfile` with arguments `START`, `STOP`, `FRAMES=N`, `STARTFILE=name`, `EXITONCOMPLETION`, `REPEAT=N`: `Runtime/Core/Private/ProfilingDebugging/CsvProfiler.cpp:1050-1087, 1117-1121`.
* `EXITONCOMPLETION` → `RequestExit` **after** the file is finalized: `:4309-4313`. The command-line equivalent is `-ExitAfterCsvProfiling`.
* Command-line options: `-csvCaptureFrames=N` (boot capture, which includes loading and uses the legacy frame time), `-csvGpuStats` (sets `r.GPUCsvStatsEnabled 1`, giving per-pass GPU timings), `-csvCategories=a,b`, `-csvMetadata=k=v,...`, `-csvRepeat=N`, `-csvCompression=0|1`, `-csvStartOnEvent=`/`-csvStopOnEvent=` (match `CSV_EVENT` text), `-csvExecCmds=`: `:5049, :5098-5186, :5204`.
* Output folder: `FPaths::ProfilingDir() + "CSV/"` = **`<Project>/Saved/Profiling/CSV/Profile(YYYYMMDD_HHMMSS).csv`** (`:4741`, `:3973-3975`, `Runtime/Core/Private/Misc/Paths.cpp:548-551`). A `.csv.gz` is written only if compression is on (`csv.CompressionMode`, `:184-191`, `:3970`).
* Per-frame columns (ms): `FrameTime` (`:4388`), `GameThreadTime`, `RenderThreadTime`, `GPUTime` (`LaunchEngineLoop.cpp:1518-1520`, from `RHIGetGPUFrameCycles`), plus memory stats such as `MemoryFreeMB` and `PhysicalUsedMB` (`CsvProfiler.cpp:4186-4190`).
* File layout: a header row whose first column is `EVENTS`, then one row per frame, then **a second header row at the end** (columns that appear mid-capture are only fully listed there), then `[Key],value` metadata (`CsvProfiler.cpp:3058-3068, 3135-3160`).

**Command (60 fps × 90 s ≈ 5400 frames; adjust):**
```bash
"$UE" "$P" /Game/Twilight/Maps/L_Vahagn -game -windowed -ResX=1600 -ResY=900 -nosplash -unattended \
   -NOSCREENMESSAGES -nosound -AutoPlayTest=600 -AutoGod \
   -ExecCmds="r.VSync 0, t.MaxFPS 0, CsvProfile EXITONCOMPLETION, CsvProfile FRAMES=5400"
```
`EXITONCOMPLETION` must come **before** `FRAMES=`. Both run in order on the first tick (ParseExecCommands keeps the order). The first 1–3 s contain PSO and shader hitches, so the parser below skips them.

**Parser** (`csv_summary.py`, Python 3 standard library only; run it with `python3 -I`):
```python
#!/usr/bin/env python3
import csv, sys, glob, os, statistics
path = sys.argv[1] if len(sys.argv) > 1 else max(glob.glob(os.path.expanduser(
    '/var/www/html/Twilight/Game/Saved/Profiling/CSV/*.csv')), key=os.path.getmtime)
skip_s = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
rows = list(csv.reader(open(path, newline='', encoding='utf-8', errors='replace')))
hdr_idx = [i for i, r in enumerate(rows) if r and r[0] == 'EVENTS']
hdr = rows[hdr_idx[-1]]                       # the last header is the complete one
data = [r for r in rows[hdr_idx[0]+1: hdr_idx[-1]] if r and not r[0].startswith('[')]
col = {n: i for i, n in enumerate(hdr)}
def series(name):
    i = col.get(name);  out = []
    if i is None: return out
    for r in data:
        try: out.append(float(r[i]))
        except (IndexError, ValueError): pass
    return out
ft = series('FrameTime')
acc, k = 0.0, 0
while k < len(ft) and acc < skip_s * 1000: acc += ft[k]; k += 1   # skip the warm-up
ft = ft[k:]
def pct(v, p):
    s = sorted(v); return s[min(len(s)-1, int(round(p/100*(len(s)-1))))]
avg_fps = 1000.0 * len(ft) / sum(ft)
out = [f"file={path}", f"frames={len(ft)} duration_s={sum(ft)/1000:.1f}",
       f"avg_fps={avg_fps:.1f}  (1% low fps={1000/pct(ft,99):.1f}, 0.1% low fps={1000/pct(ft,99.9):.1f})",
       "frametime_ms p50={:.2f} p90={:.2f} p95={:.2f} p99={:.2f} max={:.2f}".format(
           pct(ft,50), pct(ft,90), pct(ft,95), pct(ft,99), max(ft)),
       "hitches>33ms={}  >50ms={}".format(sum(x>33.3 for x in ft), sum(x>50 for x in ft))]
for name in ('GameThreadTime', 'RenderThreadTime', 'GPUTime'):
    s = series(name)[k:]
    if s: out.append(f"{name}: avg={statistics.fmean(s):.2f} p95={pct(s,95):.2f} ms")
print("\n".join(out))
```
```bash
python3 -I csv_summary.py > /var/www/html/Twilight/docs/perf_$(date +%H%M).txt
```
Interpretation: if `GPUTime` ≈ `FrameTime`, the run is GPU-bound and the fixes are in section 4. If `GameThreadTime` is close, the run is CPU-bound (Tick, AI, too many actors).

The engine's own C# CSV tools are available as an alternative: `Engine/Binaries/DotNET/CsvTools/CsvToSvg.dll` and `PerfReportTool` (run with `dotnet`, UNVERIFIED that the runtime is installed).

### 2.2 Option B: FPSChart (`startfpschart` / `stopfpschart`)
* Commands: `STARTFPSCHART [label]` → `StartFPSChart(Label, bRecordPerFrameTimes=true)`, and `STOPFPSCHART` (`Runtime/Engine/Private/UnrealEngine.cpp:5826-5833, 6665-6679`).
* Output folder: `Saved/Profiling/FPSChartStats/<capture start time>/` (`Runtime/Engine/Private/ChartCreation.cpp:1243`) with:
  * `*.log`: a text summary with "N frames collected over X seconds ... for a **Y FPS average**", "Average GPU/RenderThread/GameThread frametime", and "BoundGPUPct" (`ChartCreation.cpp:157-211, 916`)
  * `*.html` chart (`:922`)
  * `FPS-<map>.csv` with **only the 25/50/75th percentiles** plus per-frame times (`:1183-1210, 1591`)
  * With `t.FPSChart.DoCsvProfile 1` it also writes a full CSV profile into the same folder (`:58-62, 1560-1570`).
* It is limited to the 25/50/75 percentiles, so use Option A for p95/p99. FPSChart is handy as a second opinion: `-ExecCmds="startfpschart"`, then `stopfpschart` from C++ or the console before quitting. Note that `-seconds` exit does **not** call `stopfpschart`.

### 2.3 Live numbers
`stat fps` and `stat unit` draw only on screen. They are fine on screenshots, and `-statunit` turns on `stat unit` at boot. `stat unitgraph` shows a graph. None of them write to the log.

---

## 3. Screenshots and video for self-review

### 3.1 In-engine
* `Shot` / `Screenshot [showui] [filename=...]`: `Runtime/Engine/Private/GameViewportClient.cpp:3585, 4288-4301`. `HighResShot <WxH | multiplier> [filename=...]`: `GameViewportClient.cpp:3577`, arguments parsed in `Runtime/Engine/Private/UnrealClient.cpp:2433-2500` ("HighResShot 1920x1080" or "HighResShot 2").
* Output folder: `FPaths::ScreenShotDir()` = `<Project>/Saved/Screenshots/<PlatformName>/` (`Paths.cpp:553-556`). That is **`Saved/Screenshots/LinuxEditor/`** with the editor binary and `Saved/Screenshots/Linux/` in a packaged build.
* `HighResShot` renders without UI. Use `Shot showui` (or `bShowUI=true` in `RequestScreenshot`) to include the HUD.
* Use `-ExecCmds="HighResShot 1"` only for a first-frame picture. For timed shots use the C++ hook (1.2).

### 3.2 External capture with ffmpeg (X11, verified working)
The window can be located with xdotool. With `-WinX/-WinY/-ResX/-ResY` the region is also known in advance.
```bash
OUT=/var/www/html/Twilight/docs/capture; mkdir -p "$OUT"
WID=$(xdotool search --sync --onlyvisible --name 'Twilight' | head -1)
eval "$(xdotool getwindowgeometry --shell "$WID")"        # sets X Y WIDTH HEIGHT
W=$(( WIDTH / 2 * 2 )); H=$(( HEIGHT / 2 * 2 ))           # libx264/yuv420p needs even sizes
# 30 s at 30 fps, low CPU (ultrafast), mouse hidden
ffmpeg -hide_banner -loglevel error -y -f x11grab -draw_mouse 0 -framerate 30 \
       -video_size ${W}x${H} -i :0.0+${X},${Y} -t 30 \
       -c:v libx264 -preset ultrafast -crf 20 -pix_fmt yuv420p "$OUT/run_$(date +%H%M%S).mp4"
# Alternative: capture by window id (follows the window): -window_id "$WID" -i :0.0
```
* x11grab options confirmed with `ffmpeg -h demuxer=x11grab`: `-window_id`, `-video_size`, `-framerate`, `-draw_mouse`, `-follow_mouse`, `-show_region`.
* Static ffmpeg has **no VAAPI**, so encoding runs on the CPU. At 1600x900, 30 fps, ultrafast, that costs about one to two cores (UNVERIFIED estimate). It also shares memory bandwidth with the iGPU, so **expect a few % lower FPS while recording. Do not take FPS numbers from recorded runs.**
* No audio: the static build has ALSA but no Pulse. Video only is enough for review.

Frame extraction for review (one frame per second, plus a 4x3 contact sheet every 2.5 s):
```bash
V=$(ls -t "$OUT"/run_*.mp4 | head -1); mkdir -p "$OUT/frames"
ffmpeg -hide_banner -loglevel error -y -i "$V" -vf fps=1 "$OUT/frames/f_%03d.png"
ffmpeg -hide_banner -loglevel error -y -i "$V" -vf "fps=1/2.5,scale=480:-1,tile=4x3" -frames:v 1 "$OUT/contact_sheet.png"
```
Pull frames at the exact moments of hitches with `-ss <sec>`. The hitch timestamps come from the CSV, by summing FrameTime.

Full-screen grab without the window: `-video_size 1920x1200 -i :0.0+0,0`. A single desktop screenshot: `scrot -o file.png` or `ffmpeg -f x11grab -video_size 1920x1200 -i :0.0 -frames:v 1 shot.png`.

---

## 4. Rendering settings for Iris Xe that still look premium

### 4.1 Decisions (and why)

| Feature | Choice | Reason / source |
|---|---|---|
| Dynamic GI | `r.DynamicGlobalIlluminationMethod=0` (None). Movable SkyLight (real-time capture) + SkyAtmosphere + emissive "fake bounce" | Lumen is the single biggest GPU cost and is far too slow on a 96-EU iGPU. Values: 0 None, 1 Lumen, 2 SSGI, 3 Plugin (`Runtime/Renderer/Private/IndirectLightRendering.cpp:93-98`). SSGI (2) is a cheap option for Epic only. |
| Reflections | `r.ReflectionMethod=2` (SSR) with SSR quality per scalability level, or 0 plus reflection captures | Values: 0 None, 1 Lumen, 2 SSR (`IndirectLightRendering.cpp:104-107`). SSR gives the purple sea its sunset reflections. Half-res at quality ≤2 (`BaseScalability.ini [ReflectionQuality@1/2]`). |
| Shadows | `r.Shadow.Virtual.Enable=0`, classic CSM with 2–3 cascades, MaxCSMResolution 1024–2048, and a short dynamic shadow distance (about 15–30 k uu) on the sun | VSM also needs Nanite support (`Runtime/RenderCore/Private/RenderUtils.cpp:1522-1526`) and is costly. Set the shadow distance on the DirectionalLight (`dynamic_shadow_distance_movable_light`), because in the sky only the hero, close vishaps and nearby peaks need shadows. |
| Nanite / distance fields / HW RT / MegaLights | all off (`r.Nanite.ProjectEnabled=False`, `r.GenerateMeshDistanceFields=False`, `r.RayTracing=False`, `r.MegaLights.EnableForProject=0`, the default per `Renderer/Private/MegaLights/MegaLights.cpp:27`) | Cost, plus shader-compile time. |
| AA / upscaling | **TSR (4) at 67–75 % screen percentage**, AntiAliasingQuality 1–2. Fallback: TAA (2) at 75–83 %. | Values: 0 off, 1 FXAA, 2 TAA, 3 MSAA (forward only), 4 TSR (default), 5 SMAA (`Runtime/Engine/Private/SceneView.cpp:236-246`). TSR reconstructs the lower internal resolution best, but it costs 1–2 ms on the iGPU (UNVERIFIED); measure both with section 2. |
| Screen percentage | Through `sg.ResolutionQuality` (which sets `r.ScreenPercentage` at scalability priority, `Runtime/Engine/Private/Scalability.cpp:525-545`) or `UGameUserSettings::SetResolutionScaleNormalized` | `r.ScreenPercentage` ≤0 means "use r.ScreenPercentage.Default" (`Runtime/Engine/Private/LegacyScreenPercentageDriver.cpp:13-43`). |
| Dynamic resolution | Optional: `r.DynamicRes.OperationMode=2`, Min 50, Max 100, `r.DynamicRes.FrameTimeBudget=16.6` | Supported on Vulkan (`Runtime/VulkanRHI/Private/VulkanGenericPlatform.h:106`, `VulkanRHI.cpp:896`). Modes: `UnrealEngine.cpp:539-545`. Cvars: `Runtime/Engine/Private/DynamicResolution.cpp:15-111`. It keeps 60 fps during heavy boss VFX. Turn it on only after a fixed-resolution baseline exists. |
| Bloom | `r.BloomQuality=4–5` with **Gaussian (Standard) bloom** in the PostProcessVolume, not Convolution (FFT) | The default is 5 and the range is 0..5 (`Runtime/Core/Private/HAL/ConsoleManager.cpp:4081-4090`). Convolution bloom (`EBloomMethod::BM_FFT`, `Runtime/Engine/Classes/Engine/Scene.h:54-59`) is expensive on an iGPU. Gaussian bloom on emissive fire is the cheapest "premium" look there is. |
| Light shafts | DirectionalLight "Light Shaft Bloom" + `r.LightShaftQuality=1` | A cheap screen-space sunset god-ray look (cvar in `Renderer/Private/LightShaftRendering.cpp`). |
| Volumetric fog | Medium/High: `r.VolumetricFog=1`, `GridPixelSize=16`, `GridSizeZ=64` (Base @2 values). Low: off, with plain exponential height fog plus light shafts. | Cost is usually 1–3 ms at 900p on an iGPU (UNVERIFIED). Measure it; it is the first thing to drop if the GPU time exceeds 16 ms. |
| Translucency (fire VFX) | `r.SeparateTranslucencyScreenPercentage=50–75` on lower levels; limit overdraw in Niagara (fewer and larger sprites, SubUV flipbooks, short lifetimes); `fx.Niagara.QualityLevel` follows EffectsQuality | Cvar: `Runtime/Renderer/Private/TranslucentRendering.cpp:90-94`. Particle overdraw is the most likely iGPU killer in this game. |
| Motion blur / auto exposure | Off (already in the project: `r.DefaultFeature.MotionBlur=False`, `AutoExposure=False`) | Saves cost and gives a stable look. |
| Shading path | **Keep deferred.** | Forward (`r.ForwardShading=1`, `RenderUtils.cpp:738`) helps bandwidth and enables MSAA, but it recompiles every shader, changes how materials look, and loses some screen-space features (UNVERIFIED list). Too risky at this stage. |
| Mobile renderer (`-es31`/preview) | **No.** | It needs `SF_VULKAN_ES31` in TargetedRHIs, which means a second shader set and double cook time, plus a different material look. The forcing path is `LinuxDynamicRHI.cpp:18-21` and `VulkanGenericPlatform.cpp:40-46`. |
| Feature level | SM6 (current project setting). The device reports the 64-bit atomics and subgroup features. **Check the log for `Vulkan RHI ShaderPlatform for SM6: SF_VULKAN_SM6`** (`VulkanRHI.cpp:415`). If the profile check fails, UE "Skipping"s the format (`LinuxDynamicRHI.cpp:120-124`) and, with only SM6 targeted, gets **no Vulkan RHI**. Keep **only one** Vulkan format in TargetedRHIs (halves cook time). Switch to SM5 only if SM6 fails. | UNVERIFIED at runtime on this machine (no logs yet). |
| VSync / frame cap | Tests: `r.VSync 0, t.MaxFPS 0`. **Presentation: `r.VSync=1`, `t.MaxFPS=60`.** | The project now has `t.MaxFPS=120, r.VSync=0`, which tears on a projector and makes frame pacing uneven on a 60 Hz panel. |

**Important priority trap (verified):** cvar priority is `Scalability (0x02) < ProjectSetting (0x04) < SystemSettingsIni (0x05) < DeviceProfile (0x07) < ConsoleVariablesIni < Commandline < Code < Console` (`Runtime/Core/Public/HAL/IConsoleManager.h:155-187`). A cvar placed in `DefaultEngine.ini [SystemSettings]` **overrides the scalability groups**, so an in-game quality toggle stops affecting it. Put every quality-dependent cvar into `DefaultScalability.ini` group sections only. Put only project-wide switches into `[/Script/Engine.RendererSettings]` and `[SystemSettings]`.

### 4.2 Recommended `Config/DefaultEngine.ini` additions (merge with the current file)
```ini
[/Script/Engine.RendererSettings]
; --- already present in the project, keep ---
r.DynamicGlobalIlluminationMethod=0
r.ReflectionMethod=2
r.Shadow.Virtual.Enable=0
r.GenerateMeshDistanceFields=False
r.Nanite.ProjectEnabled=False
r.RayTracing=False
r.AllowStaticLighting=False
r.DefaultFeature.AutoExposure=False
r.DefaultFeature.MotionBlur=False
r.DefaultFeature.Bloom=True
r.AntiAliasingMethod=4
r.SkinCache.CompileShaders=True
; --- add ---
r.Lumen.HardwareRayTracing=False
r.MegaLights.EnableForProject=0
r.DefaultFeature.LensFlare=False        ; cheap, but looks cheap. Use authored flares/sprites instead
r.SkyLight.RealTimeReflectionCapture=1  ; dynamic sky ambient without Lumen (verify the look; cost is time-sliced)
r.DynamicRes.OperationMode=0            ; set to 2 later if the GPU stays near budget (see 4.1)
r.DynamicRes.MinScreenPercentage=50
r.DynamicRes.MaxScreenPercentage=100
r.DynamicRes.FrameTimeBudget=16.6

[/Script/LinuxTargetPlatform.LinuxTargetSettings]
-TargetedRHIs=SF_VULKAN_SM5
+TargetedRHIs=SF_VULKAN_SM6               ; exactly one format → one shader set, faster cook

[SystemSettings]
; Not scalability-controlled (safe here). Presentation values:
r.VSync=1
t.MaxFPS=60
```
Do **not** put `r.Streaming.PoolSize`, `r.ScreenPercentage`, `r.VolumetricFog`, `r.BloomQuality`, shadow cvars and similar into `[SystemSettings]`, because of the priority trap. Linux sets the texture pool to 70 % of the reported VRAM (`Engine/Config/Linux/LinuxEngine.ini [TextureStreaming] PoolSizeVRAMPercentage=70`). `GRHIDeviceIsIntegrated` is detected (`VulkanRHI.cpp:1170`). If textures look blurry, raise `r.Streaming.PoolSize` inside the TextureQuality groups (below).

### 4.3 Recommended `Config/DefaultScalability.ini` (overrides `Engine/Config/BaseScalability.ini`, same section names)
The engine default quality level is **3 (Epic)** for every group when no saved user settings exist (`Runtime/Engine/Public/Scalability.h:21`). Epic is therefore what runs on first launch. Make **@3 the tuned "Presentation" preset** for this iGPU and keep @2 as the fallback:
```ini
[ScalabilitySettings]
PerfIndexValues_ResolutionQuality="50 60 67 75 100"   ; used only by auto-detect

;----------------------- Shadows -----------------------
[ShadowQuality@2]
r.ShadowQuality=3
r.Shadow.CSM.MaxCascades=2
r.Shadow.MaxResolution=1024
r.Shadow.MaxCSMResolution=1024
r.Shadow.DistanceScale=0.7
r.Shadow.RadiusThreshold=0.05
r.DistanceFieldShadowing=0
r.VolumetricFog=0
r.CapsuleShadows=0
r.ContactShadows=1

[ShadowQuality@3]
r.ShadowQuality=4
r.Shadow.CSM.MaxCascades=3
r.Shadow.MaxResolution=1024
r.Shadow.MaxCSMResolution=2048
r.Shadow.DistanceScale=0.85
r.Shadow.RadiusThreshold=0.04
r.DistanceFieldShadowing=0
r.VolumetricFog=1
r.VolumetricFog.GridPixelSize=16
r.VolumetricFog.GridSizeZ=64
r.VolumetricFog.HistoryMissSupersampleCount=2
r.CapsuleShadows=0
r.ContactShadows=1

;----------------------- GI / Reflections -----------------------
[GlobalIlluminationQuality@2]
r.DistanceFieldAO=0
r.AOQuality=1
r.Lumen.DiffuseIndirect.Allow=0
r.SkylightIntensityMultiplier=1.0
[GlobalIlluminationQuality@3]
r.DistanceFieldAO=0
r.AOQuality=1
r.Lumen.DiffuseIndirect.Allow=0
r.SkylightIntensityMultiplier=1.0

[ReflectionQuality@2]
r.SSR.Quality=1
r.SSR.HalfResSceneColor=1
r.Lumen.Reflections.Allow=0
[ReflectionQuality@3]
r.SSR.Quality=2
r.SSR.HalfResSceneColor=1
r.Lumen.Reflections.Allow=0

;----------------------- Post -----------------------
[PostProcessQuality@2]
r.BloomQuality=4
r.LightShaftQuality=1
r.AmbientOcclusionLevels=1
r.AmbientOcclusionMaxQuality=50
r.DepthOfFieldQuality=0
r.MotionBlurQuality=0
r.LensFlareQuality=0
r.SceneColorFringeQuality=0
r.Tonemapper.Quality=1
[PostProcessQuality@3]
r.BloomQuality=5
r.LightShaftQuality=1
r.AmbientOcclusionLevels=1
r.AmbientOcclusionMaxQuality=75
r.DepthOfFieldQuality=1
r.MotionBlurQuality=0
r.LensFlareQuality=0
r.SceneColorFringeQuality=1
r.Tonemapper.Quality=3

;----------------------- Effects (fire) -----------------------
[EffectsQuality@2]
r.SeparateTranslucencyScreenPercentage=60
r.TranslucencyLightingVolume.Dim=32
r.RefractionQuality=1
r.SSGI.Quality=0
fx.Niagara.QualityLevel=2
r.MaterialQualityLevel=1
[EffectsQuality@3]
r.SeparateTranslucencyScreenPercentage=75
r.TranslucencyLightingVolume.Dim=48
r.RefractionQuality=2
r.SSGI.Quality=0
fx.Niagara.QualityLevel=3
r.MaterialQualityLevel=1

;----------------------- AA -----------------------
[AntiAliasingQuality@2]
r.TSR.History.ScreenPercentage=100
r.TSR.History.UpdateQuality=1
r.TSR.ShadingRejection.Flickering=1
r.TSR.RejectionAntiAliasingQuality=1
r.TSR.ReprojectionField=0
[AntiAliasingQuality@3]
r.TSR.History.ScreenPercentage=100     ; Base Epic uses 200: expensive on an iGPU
r.TSR.History.UpdateQuality=2
r.TSR.ShadingRejection.Flickering=1
r.TSR.RejectionAntiAliasingQuality=1
r.TSR.ReprojectionField=1

;----------------------- Textures -----------------------
[TextureQuality@3]
r.Streaming.PoolSize=1500
r.Streaming.LimitPoolSizeToVRAM=0
r.MaxAnisotropy=8
```
Notes:
* Only keys that differ from Base need to be listed. A section in `DefaultScalability.ini` overrides the matching keys of the same section in Base. Base values are quoted from `Engine/Config/BaseScalability.ini` (for example `[ShadowQuality@2]` at lines 202-238, `[PostProcessQuality@2]` at 621-656, `[EffectsQuality@2]` at 856-887).
* `r.MaterialQualityLevel=0` (Base `EffectsQuality@0`) switches materials to their Low branch. Avoid level 0 for Effects in the presentation.
* `fx.Niagara.QualityLevel` is defined in the Niagara plugin (`Engine/Plugins/FX/Niagara/Source/Niagara/Private/NiagaraPlatformSet.cpp`).
* Starting scalability for a fresh install: `Config/DefaultGameUserSettings.ini` can carry a `[ScalabilityGroups]` section with `sg.ResolutionQuality=70`, `sg.ShadowQuality=3`, and so on. `Scalability::LoadState` reads that section from `GGameUserSettingsIni` (`Scalability.cpp:1172-1190`). The Default→Saved layering is standard (`Engine/Config/BaseGameUserSettings.ini` exists). UNVERIFIED by a run. Remember that a stale `Saved/Config/<Platform>/GameUserSettings.ini` overrides it, so delete it before the presentation or apply settings in code.

### 4.4 In-game quality toggle (C++ API verified in `Runtime/Engine/Classes/GameFramework/GameUserSettings.h`)
`GetGameUserSettings()` (:375), `SetOverallScalabilityLevel(int32)` (:176), `SetResolutionScaleNormalized(float)` (:196), `SetVSyncEnabled(bool)` (:115), `SetFrameRateLimit(float)` (:167), `SetDynamicResolutionEnabled(bool)` (:123), `SetShadowQuality/SetGlobalIlluminationQuality/SetPostProcessingQuality` (:210/219/264), `ApplySettings(bool bCheckForCommandLineOverrides)` (:49, also saves), `RunHardwareBenchmark` / `ApplyHardwareBenchmarkResults` (:379/383).
```cpp
#include "GameFramework/GameUserSettings.h"
void ATwPlayerController::SetQualityPreset(int32 Level /*1=Performance, 2=Balanced, 3=Presentation*/)
{
    UGameUserSettings* S = UGameUserSettings::GetGameUserSettings();
    S->SetOverallScalabilityLevel(FMath::Clamp(Level, 0, 3));
    static const float Scale[] = {0.50f, 0.60f, 0.67f, 0.75f};          // normalized resolution scale
    S->SetResolutionScaleNormalized(Scale[FMath::Clamp(Level, 0, 3)]);
    S->SetVSyncEnabled(true);
    S->SetFrameRateLimit(60.f);
    S->ApplySettings(false);
}
// Bind to F1/F2/F3 (or a small menu). At first start (e.g. GameInstance::Init) call SetQualityPreset(3)
// so the result does not depend on a stale Saved/Config file.
```
Do not use `RunHardwareBenchmark` for the demo. It is nondeterministic and could pick Low on a hot laptop. Choose the preset explicitly after measuring.

Quick A/B from the command line, with no rebuild: `-ExecCmds="sg.ShadowQuality 2, sg.PostProcessQuality 3, r.ScreenPercentage 67"`, or `scalability 2` (console).

### 4.5 Budget and expectation
Target **60 fps = 16.6 ms GPU** at 1920x1200 output with a 67–75 % internal resolution (about 1290–1440 x 800–900). Expected order of magnitude on Iris Xe (UNVERIFIED, to be measured): base pass + CSM ≈ 4–6 ms, TSR ≈ 1–2 ms, bloom/tonemap ≈ 1 ms, volumetric fog ≈ 1–3 ms, fire translucency 1–6 ms (depends on overdraw). If the p95 GPUTime is above 16 ms, cut in this order: volumetric fog → screen percentage → translucency resolution → shadow cascades → SSR.

---

## 5. Startup time, shader compilation and PSO warm-up; packaging

### 5.1 Where shaders and caches live (verified)
* **DDC** graph: `(ProjectPak, EnginePak, ZenLocal, Local, ZenShared, Shared, Cloud)` (`Engine/Config/BaseEngine.ini:2788`). Zen auto-launches (`[Zen] AutoLaunch=true`, data path `%ENGINEVERSIONAGNOSTICINSTALLEDUSERDIR%Zen/Data`), which on this machine is **`~/.config/Epic/UnrealEngine/Common/Zen/Data`** (exists, 421 MB). The filesystem fallback is `Engine/DerivedDataCache` (`BaseEngine.ini:2866`, 260 MB). **Do not delete these folders before the presentation.**
* **Vulkan PSO binary cache**: `<Project>/Saved/VulkanProgramBinaryCache/` (`Runtime/VulkanRHI/Private/VulkanGenericPlatform.cpp:95-98`), loaded when `r.Vulkan.PipelineCacheLoad=1` (default, `VulkanPipeline.cpp:104-108`). Chunked cache: `Saved/RHICache/<RHIName>/` (`VulkanChunkedPipelineCache.cpp:181`).
* **Mesa driver cache**: `~/.cache/mesa_shader_cache*`. Mesa's default maximum size is about 1 GB (UNVERIFIED for 25.2). Raise it with `export MESA_SHADER_CACHE_MAX_SIZE=4G` in the launch script, so a full playthrough is not evicted.
* **PSO precaching** is on by default (`r.PSOPrecaching=1`, `Runtime/RHI/Private/PipelineStateCache.cpp:210-217`). It compiles PSOs when components load, but it is not a guarantee against first-use hitches. Niagara and dynamic material instances often still hitch once.

### 5.2 Pre-warm procedure (works for both the editor `-game` route and a packaged build)
1. After the **final** content and config change, run the game once with the full autoplay (`-AutoPlayTest=480 -AutoGod`). Every wave, the boss, victory **and** defeat screens, and every VFX should appear. Then run it once more and confirm in the CSV that `hitches>50ms` ≈ 0 after warm-up.
2. Do this **on the presentation laptop itself, at the presentation resolution and quality preset.** The PSO and driver caches are specific to the GPU, driver and settings (the PSO cache folder name includes vendor and device ID, `VulkanGenericPlatform.cpp:85-90`).
3. Do not run with `-clearPSODriverCache` and do not clear `~/.cache` after that.
4. Optional, more formal route (only if hitches remain): record PSOs with `-logPSO` in a packaged Development build (written to `Saved/CollectedPSOs/*.upipelinecache`, `PipelineFileCache.cpp:2290`), copy them to `Game/Build/Linux/PipelineCaches/`, recook so they become the bundled `ShaderPipelineCache`, and tune `r.ShaderPipelineCache.*` (`Runtime/RenderCore/Private/ShaderPipelineCache.cpp:56-185`). This costs a second cook and is probably not worth it in the time available (UNVERIFIED workflow details for 5.8).

First-launch shader compilation with the editor binary will take a while (global shaders + every material + Niagara, SM6 only). Estimate 10–40 min on 20 threads (UNVERIFIED). Later launches read from Zen DDC and take seconds to a minute.

### 5.3 Editor `-game` vs packaged build for the presentation
| | Editor binary `-game` | Packaged Linux Development/Shipping |
|---|---|---|
| Extra build needed | none | **A full monolithic engine compile for the game target** (no game target has been built yet) plus a cook |
| Load time | slower (uncooked) | fast |
| Shader risk | material shaders compile on demand if the DDC is missing → default-material pop-in on first sight | all shaders cooked |
| Tools (ExecCmds, CSV, `-seconds`) | yes | Development: yes. Shipping: no |

**Recommendation:** develop and test with the editor `-game` route tonight. Start a packaging run once the CPU is free, because it takes hours the first time. Present with the packaged build if it is ready and tested, otherwise with the editor `-game` route after pre-warming (5.2).

### 5.4 Packaging command (parameter names verified in `Engine/Source/Programs/AutomationTool/AutomationUtils/ProjectParams.cs` and `AutomationTool/Program.cs:296-302`)
```bash
/home/samo/UnrealEngine-5.8/Engine/Build/BatchFiles/RunUAT.sh BuildCookRun \
  -project=/var/www/html/Twilight/Game/Twilight.uproject \
  -noP4 -utf8output -unattended \
  -platform=Linux -clientconfig=Development \
  -build -cook -stage -pak -iostore \
  -map=/Game/Twilight/Maps/L_Vahagn \
  -archive -archivedirectory=/var/www/html/Twilight/Build \
  -nocompileeditor \
  2>&1 | tee /var/www/html/Twilight/docs/package_$(date +%m%d_%H%M).log
```
* Shipping build: `-clientconfig=Shipping` (add `-nodebuginfo` for a smaller output, `ProjectParams.cs:964`). This loses ExecCmds, CSV and `-seconds`.
* For repeated packaging after small changes, add **`-cookincremental`** (aliases `-iterativecooking`/`-iterate`, `ProjectParams.cs:34, 866`). After code-only changes, `-skipcook` (`:794`).
* `-nocompileeditor` (= `-skipbuildeditor`, `:743`) assumes the editor and the project's editor module are already built. The main agent builds them.
* The archive output is `Build/Linux/` with a `Twilight.sh` launcher and `Twilight/Binaries/Linux/Twilight` (layout is standard, UNVERIFIED for 5.8). UAT logs go to `Engine/Programs/AutomationTool/Saved/Logs/`.
* Toolchain: the bundled clang SDK is present (`Engine/Extras/ThirdPartyNotUE/SDKs/HostLinux/Linux_x64/v26_clang-20.1.8-rockylinux8`).
* **Expected time (UNVERIFIED estimates for i7-13700H, 30 GB RAM):** the first Development game-target compile rebuilds the engine as a monolithic game binary, roughly **60–150 min**. UBT limits parallel actions by RAM, and the editor shares the CPU. The first cook with shaders (SM6 only) takes about **20–60 min**. Stage, pak and iostore take about 2–5 min. Later incremental package runs take about **5–20 min**. Run the packaged build once with the autoplay (5.2) before trusting it.

Run the packaged build:
```bash
/var/www/html/Twilight/Build/Linux/Twilight.sh -windowed -ResX=1600 -ResY=900 -nosplash \
   -AutoPlayTest=300 -AutoGod -ExecCmds="r.VSync 0, t.MaxFPS 0"
# presentation:
MESA_SHADER_CACHE_MAX_SIZE=4G /var/www/html/Twilight/Build/Linux/Twilight.sh -fullscreen -nosplash -NOSCREENMESSAGES
```

---

## 6. One-shot overnight test script (proposal)

`/var/www/html/Twilight/tools/perf_run.sh`. The main agent decides where it lives; it reads the project but does not modify it:
```bash
#!/usr/bin/env bash
set -euo pipefail
UE=/home/samo/UnrealEngine-5.8/Engine/Binaries/Linux/UnrealEditor
P=/var/www/html/Twilight/Game/Twilight.uproject
OUT=/var/www/html/Twilight/docs/perf/$(date +%m%d_%H%M); mkdir -p "$OUT"
export MESA_SHADER_CACHE_MAX_SIZE=4G
QUAL=${1:-3}; SECS=${2:-300}
"$UE" "$P" /Game/Twilight/Maps/L_Vahagn -game -windowed -ResX=1600 -ResY=900 -WinX=160 -WinY=150 \
  -nosplash -unattended -NOSCREENMESSAGES -nosound -stdout -FullStdOutLogOutput \
  -AutoPlayTest="$SECS" -AutoGod -AutoWarmup=10 -AutoShotEvery=20 \
  -ExecCmds="r.VSync 0, t.MaxFPS 0, scalability $QUAL" > "$OUT/game.log" 2>&1 &
GPID=$!
sleep 40   # skip boot, then record 30 s of video
WID=$(xdotool search --sync --onlyvisible --name 'Twilight' | head -1)
eval "$(xdotool getwindowgeometry --shell "$WID")"
ffmpeg -hide_banner -loglevel error -y -f x11grab -draw_mouse 0 -framerate 30 \
  -video_size $((WIDTH/2*2))x$((HEIGHT/2*2)) -i :0.0+${X},${Y} -t 30 \
  -c:v libx264 -preset ultrafast -crf 20 -pix_fmt yuv420p "$OUT/clip.mp4" || true
wait $GPID || true
ffmpeg -hide_banner -loglevel error -y -i "$OUT/clip.mp4" -vf "fps=1/2.5,scale=480:-1,tile=4x3" -frames:v 1 "$OUT/sheet.png" || true
CSV=$(ls -t /var/www/html/Twilight/Game/Saved/Profiling/CSV/*.csv | head -1)
cp "$CSV" "$OUT/"; python3 -I /var/www/html/Twilight/tools/csv_summary.py "$CSV" 3 | tee "$OUT/summary.txt"
cp /var/www/html/Twilight/Game/Saved/Screenshots/LinuxEditor/auto_*.png "$OUT/" 2>/dev/null || true
grep -E "Vulkan RHI ShaderPlatform|Integrated GPU|Error|Ensure|Fatal" "$OUT/game.log" | head -50 > "$OUT/log_highlights.txt" || true
```
Notes: the FPS from the run with the 30 s recording is a little pessimistic. For a clean number, run once with no recording. The review images to examine are `sheet.png` and `auto_*.png`. They can be opened with the Read tool, which shows images, so effects can be checked for anything that looks wrong or unrealistic.

---

## 7. Open items / UNVERIFIED list
1. SM6 profile acceptance on Iris Xe + Mesa 25.2 (check the log line `VulkanRHI.cpp:415`).
2. The exact UE window title string, needed for `xdotool search --name`.
3. Whether XTest relative mouse motion reaches UE's SDL relative mode.
4. The `EndCapture().Wait()` pattern on the game thread (the `CsvProfile EXITONCOMPLETION` fallback is verified).
5. Layering of `DefaultGameUserSettings.ini [ScalabilityGroups]` (the code path is verified, a run is not).
6. All timing estimates (shader compile, package time, per-pass ms on Iris Xe).
7. The default Mesa shader-cache size and the exact archive folder layout of 5.8 Linux packaging.
