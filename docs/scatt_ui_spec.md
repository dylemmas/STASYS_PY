# SCATT Basic → STASYS UI/UX Reverse-Engineering Spec

**Status:** engineering contract for the STASYS reskin.
**Scope:** layout structure, widget placement, interaction workflow.
**Out of scope:** SCATT backend, SCATT branding/logos (never copied).
**Repo:** `python_app/stasys_app/core.py` (STASYS target).
**Evidence root:** `scratch/scatt_extracted/`.

---

## 1. Evidence & method

### 1.1 What the evidence actually is

The SCATT QML is **compiled V4 bytecode embedded in `scattbasic.exe`**, not source.
There is **no `qml` source text anywhere** — `resource_paths.txt` lists the 114 qrc *paths*
(each ending in `.qml`), but those are **path strings**, not file contents. No line of QML
has been read by this spec, and none may be quoted as if it had.

Every structural claim below is derived from three extracted artifacts:

| Artifact | Content | Confidence it supports |
|---|---|---|
| `resource_paths.txt` (114 lines) | Complete qrc path inventory: `qml/` root, `qml/ShootingView/`, `qml/shared/` (30 widgets), `qml/style/` (~60 QtQuick Controls 2 style overrides), `:/firmware`, `:/i18n` | Which files exist. Nothing about their contents. |
| `strings_utf16.txt` (3945 lines) | UTF-16LE identifier/text pool: object IDs, property names, signal names, `expression for …` fragments, qrc paths, literal UI text | **Richest source.** Property/signal/ID names bound to a file. |
| `strings_ui.txt` (1807 lines) | ASCII strings: API symbols (`QSettings` keys, signal signatures), SQL schema, user-facing messages, embedded SVG markup | Persistence keys, data model, messages. |
| `assets/asset_*.svg` (206 files) | Carved SVG graphics | Icon inventory, some literal colours. |

### 1.2 The file-attribution method (how structure was recovered)

`strings_utf16.txt` is a sequence of per-QML-module string pools. Each pool **terminates with
its own fully-qualified qrc path** (e.g. `qrc:///qml/ShootingView/RangeView.qml`), and often
**begins** with the path of the *previous* module. Therefore:

> **Content on lines *N*…*M* belongs to the module whose terminator path sits at line *M*.**

This is the load-bearing inference of the whole document, so it is stated explicitly.
It was validated in both directions: `ShootingViewMode.qml` (line 1812) is immediately
followed by `RangeData / range / displayMode / shotListModel / Session / TargetDescriptor`
(the *arguments it passes into* `RangeView`), which is exactly what a mode shell would
carry; and `RangeView.qml`'s own pool (2255–2319) contains only title/battery/step-enum
symbols, which is what a *container* would carry. `[INFERENCE]` — strong, but not `[CONFIRMED]`.

Complete attribution table (line ranges in `strings_utf16.txt`):

| Lines | Module | Class |
|---|---|---|
| –1084 | `LanguageSelector.qml` | root |
| –1201 | `AboutMode.qml` | root mode |
| 1201–1389 | `MainWindow.qml` | app chrome |
| 1389–1578 | `SettingsEditorMode.qml` | root mode (settings) |
| 1578–1796 | `Diagnostics.qml` | dialog |
| 1796–1810 | `ShowMessageAndQuit.qml` | dialog |
| 1800/1808 | `MacOSMenuBar.qml`, `main.qml` | entry |
| 1812–2213 | `ShootingViewMode.qml` | root mode |
| 2213–2255 | `ShotList.qml` | component |
| 2255–2320 | `RangeView.qml` | **screen container** |
| 2320–2342 | `RangeView_Title.qml` | top strip |
| 2342–2368 | `BatteryIndicator.qml` | sub-widget |
| 2368–2383 | `RangeView_Emulator_debug.qml` | debug |
| 2383–2398 | `TargetListSelector.qml` | selector |
| 2398–2444 | `RangeView_CatalogMode_SessionViewStep.qml` | Catalog step 2 |
| 2444–2524 | `RangeView_PracticeMode_SelectTargetStep.qml` | Practice step |
| 2524–2537 | `RangeView_CatalogMode_SelectSessionStep.qml` | Catalog step 1 |
| 2537–2545 | `RangeView_PracticeMode_ShootingStep.qml` | Practice step |
| 2545–2548 | `RangeView_PracticeMode_SelectShooterStep.qml` | Practice step |
| 2548–2556 | `ShootingView_All.qml` | layout variant |
| 2556–2703 | `RangeView_RegionError.qml` + `RangeView_State_debug.qml` | error/debug |
| 2703–2731 | `RangeView_State_debug.qml` | debug |
| 2731–2752 | `RangeView_Timeline.qml` | bottom strip |
| 2752–2756 | `ShootingView.qml` | window manager |
| 2756–2811 | `ShootingView_Maximized.qml` | calibration overlays |
| 2811–2868 | `RangeView_PracticeMode_CalibrationStep.qml` | Practice step |
| 2868–2896 | `RangeView_TargetView_SidePane.qml` | right pane |
| 2896–2922 | `TargetGridSelector.qml` | selector |
| 2922–2933 | `RangeView_PracticeMode_ConfigureHardwareStep.qml` | Practice step |
| 2933–3083 | `RangeView_UndefinedMode.qml` + `SessionPrintout` | home / print |
| 3083–3089 | `RangeView_TargetView.qml` | center region |
| 3089–3107 | `RangeView_Footer.qml` | footer |
| 3107–3463 | `qml/style/*` (≈60 files) | SCATT theme |
| 3463–3693 | `qml/shared/*` (30 files) | reusable widgets |

> **Caveat:** the ranges for `RangeView_RegionError` (2556), `RangeView_State_debug`
> (2703) and `RangeView_UndefinedMode` (2933) are the *fuzziest* in the table — each is
> preceded by binary padding and each shares symbols with its neighbour. Treat their
> internal contents as `[INFERENCE]`; treat everything else above as high-confidence `[INFERENCE]`.
> No claim in §3 depends on those three ranges.

### 1.3 Confidence notation

- **`[CONFIRMED]`** — the literal string/ID exists verbatim in an extracted file; a path
  exists in `resource_paths.txt`. No interpretation added.
- **`[INFERENCE]`** — a reading of a name, a naming-convention convention, or the
  module-attribution method above. Reasonable and stated, but not directly readable.
- **`[UNKNOWN]`** — the evidence does not determine it. **Do not fill these in from taste.**
  Pixel spacing, exact proportions, exact padding/margins, animation durations, font sizes
  in SCATT, and default colour *values* are all `[UNKNOWN]` in this spec.

**Rule:** an unmarked guess is a defect. If a value is not tagged `[CONFIRMED]` /
`[INFERENCE]` / `[UNKNOWN]`, it must not appear as fact.

---

## 2. Navigation flow

### 2.1 Root structure

`main.qml` `[CONFIRMED]` creates the `ApplicationWindow` named `appWindow`
(also `qrc:///qml/MainWindow.qml` `[CONFIRMED]`, `QtQuick.Window / ApplicationWindow`) which
owns a `header` (`ToolBar`) and a `StackView` named `stack` with `initialItem`
`[CONFIRMED]` — see §3.1.

```
main.qml  ──loads──►  MainWindow.qml  (ApplicationWindow "appWindow")
                        │
                        ├─ header : ToolBar                     [CONFIRMED]
                        │    ├─ logo image  qrc:/images/scatt_logo_48px.svg   [CONFIRMED]
                        │    ├─ ToolButton  (autoExclusive, checkable) ── mode switch  [CONFIRMED]
                        │    ├─ ImageToolButton "attentionButton"
                        │    │      icon qrc:/images/ic_report_48px.svg       [CONFIRMED]
                        │    │      SequentialAnimation opacity / Infinite / InOutQuad  [CONFIRMED]
                        │    ├─ fullScreenButton  (ic_fullscreen_48px / ic_fullscreen_exit_48px)
                        │    │      tooltips: "Display the window in full screen"
                        │    │                "Leave the full screen mode!"   [CONFIRMED]
                        │    └─ Shortcut Ctrl+Q → confirmQuit popup           [CONFIRMED]
                        │
                        ├─ StackView "stack"                    [CONFIRMED]
                        │    initialItem  ⇄  replace(key + ".qml")            [CONFIRMED]
                        │    (key = mode name; "qrc:/qml/" + key + ".qml")     [CONFIRMED]
                        │    shortcuts: Ctrl+Tab, Ctrl+Shift+Tab → nextMode / prevMode  [CONFIRMED]
                        │
                        ├─ mode title:  modeTitle / mode / "unknown mode " assert  [CONFIRMED]
                        └─ Progress overlay for storage jobs (modal Popup + ProgressBar)
                              "Deleting…", "Importing %1", "Exporting to %1",
                              jobProgress, jobCancel, "Are you sure you want to quit application?"  [CONFIRMED]
```

**Modes** (`enumAppDataMode` `[CONFIRMED]`, values confirmed from the same pool):

| Mode key | Title | File | Notes |
|---|---|---|---|
| `undefined` | *(home)* | `RangeView_UndefinedMode.qml` | launcher: "Start new practice" / "Open recent sessions" |
| `Shooting` | `ShootingViewMode` | `ShootingViewMode.qml` | **main mode** (wizard + analysis) |
| `Preferences` | `SettingsEditorMode` | `SettingsEditorMode.qml` | settings |
| `About` | `AboutMode` | `AboutMode.qml` | about |

Navigation signals confirmed: `nextMode`, `prevMode`, `gotoSettings`, `gotoAbout`,
`gotoDiagnistics` `[sic]`, `attentionNeeded`, `modeChanged`, `enumAppDataMode` `[CONFIRMED]`.

`MacOSMenuBar.qml` `[CONFIRMED]` — a `MenuBar`/`Menu`/`MenuItem` strip with `about.*`,
`preferences`, `gotoAbout`, `gotoSettings`, `Quit` (`qApp.quit`). Platform-only; **no
equivalent required on Windows** `[INFERENCE]`.

### 2.2 The Practice wizard (main mode)

`ShootingViewMode` hosts `ShootingView` → `RangeView`, which is a **state machine keyed on
`practiceStep`** (`enumRangeDataPracticeStep` `[CONFIRMED]`). Step order and names are
confirmed by the enum pool *and* by the `goto…Step` signals:

```
                 ┌──────────────────────────────────────────────┐
   header  ──────►  ShootingViewMode  (enumAppDataMode=Shooting) │
                 └──────────────────────────────────────────────┘
                                    │
                        ShootingView.qml  [CONFIRMED]
              (shortcut Ctrl+T toggleMaximizedRange,
               Ctrl+1 … Ctrl+8 → range slots,
               maximizedRange / RangeState_debug / Emulator_debug)
                                    │
                        RangeView.qml  [CONFIRMED]   ← the screen
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │  mode == PracticeMode     │  mode == CatalogMode      │  else
        ▼                           ▼                           ▼
  practiceStep [CONFIRMED]    catalogStep [CONFIRMED]   RangeView_UndefinedMode
        │                           │                    (home launcher)  [CONFIRMED]
        │                           │                    "Start new practice"  [CONFIRMED]
        │                           │                    "Open recent sessions" [CONFIRMED]
        ▼                           ▼
┌─ PRACTICE WIZARD ─────────┐  ┌─ CATALOG ─────────────────┐
│ 1 SelectShooterStep       │  │ 1 SelectSessionStep       │
│    "Select shooter"       │  │    (Shooters / Practices  │
│    + AddShooterPopup      │  │     lists, Import/Export/ │
│    icon scatt_ic_person   │  │     Report, Delete, Open) │
│         │                 │  │         │                 │
│         ▼ gotoConfigure…  │  │         ▼ gotoSessionView │
│ 2 ConfigureHardwareStep   │  │ 2 SessionViewStep         │
│    "Configure hardware| %1│  │    Back / Previous session │
│    Connect the sensor via:│  │    / Next session          │
│    [USB] [Wi-Fi]  [list]  │  │    + full RangeView        │
│    gotoSelectShooterStep  │  │    gotoPreviousSession     │
│    gotoSelectTargetStep   │  │    gotoNextSession         │
│         │                 │  │    gotoHome                │
│         ▼                 │  └───────────────────────────┘
│ 3 SelectTargetStep        │
│    "Select target | %1"   │
│    target grid/list + filter
│    Flow: distance / caliber / tags
│    Grid view | List view | Print target
│    Continue → gotoCalibrationStep
│         │                 │
│         ▼                 │
│ 4 CalibrationStep         │
│    "Calibration | %1 | %2 | %3%4"
│    Vision / Preview mode / Shot sensitivity
│    "Back to Shooting" · Clear target · accept/cancel
│         │                 │
│         ▼                 │
│ 5 ShootingStep  ◄─────────┴── "Calibration" button re-enters #4
│    "Practice | %1 | %2 | %3 | %4%5"
│    Stop practice · Make correction · New session
│    "Are you sure you want to restart session?"
└───────────────────────────┘
```

- Step order **`SelectShooterStep → ConfigureHardwareStep → SelectTargetStep → CalibrationStep → ShootingStep`**
  is `[CONFIRMED]`: the enum names appear in that order in the
  `enumRangeDataPracticeStep` pool (lines 2240–2250), and the forward edges
  (`gotoConfigureHardwareStep` in SelectTargetStep, `gotoSelectTargetStep` in
  ConfigureHardwareStep, `gotoCalibrationStep` in SelectTargetStep, `gotoShootingStep`,
  `cancelCalibration`/`acceptCalibration`, `calibrationReturnToShooting` → "Back to Shooting")
  are `[CONFIRMED]`.
  > **Note on the brief's stated order:** the brief lists *SelectTarget before
  > ConfigureHardware*. The evidence puts **ConfigureHardware second, SelectTarget third**
  > (`gotoSelectTargetStep` lives in the ConfigureHardware pool at line 2920; the
  > SelectTarget pool at 2439 has `gotoConfigureHardwareStep`, i.e. a *back* edge).
  > **This spec follows the evidence.** `[INFERENCE]`, moderately confident — the two
  > forward edges are confirmed but the enum's declaration order is only
  > declaration order, not necessarily execution order.
- `ShootingStep` and `SelectShooterStep` are *thin*: their pools are 8 lines and 4 lines
  respectively `[CONFIRMED]`. Most of the wizard chrome lives in `RangeView`
  (title, footer, target view) rather than in the steps.
  `[INFERENCE]`
- Reload on state change: `onRangeChanged`, `onPracticeStepChanged`, `onCatalogStepChanged`,
  `onRegionErrorChanged`, `debugStateLoader`, `debugEmulatorLoader`, `setSource`
  (`"qrc:/qml/ShootingView/" + "RangeView_" + … + ".qml"`) `[CONFIRMED]`.

### 2.3 Modes vs popups vs dialogs

**Modes** (replace the `StackView` root — one at a time):
`ShootingViewMode`, `SettingsEditorMode`, `AboutMode`, `undefined` (home).
`[CONFIRMED]`

**Screen states inside the main mode** (swap inside `RangeView`, not whole-window modes):
`RangeView_UndefinedMode`, `RangeView_RegionError`, `RangeView_State_debug`,
`RangeView_Emulator_debug`, plus the 7 wizard steps. `[CONFIRMED]` as files;
their "state not mode" classification is `[INFERENCE]`.

**Popups** (overlay, non-root; all in `qml/shared/`, all `[CONFIRMED]` as files):

| Popup | Evidence for role |
|---|---|
| `ConfirmPopup` | `messageText`, `acceptButton`, `rejectText`, `rejectButton`, `rejected`, `maximumTextWidth/Height` |
| `ButtonWithConfirmPopup` | `acceptText` — a button that arms its own confirm |
| `ButtonWithPopup` | `popupVisible` |
| `ImageToolButtonWithPopup` / `ImageToolButtonWithConfirmPopup` | icon button + popup |
| `AddShooterPopup` | `Add shooter`, `Name`, `Name already exists`, `shooterAdded`, `shooterExists` |
| `PrintTargetPopup` | `Print target - %1`, `Simulated distance…`, `Print title/border/score rings/score marks/Print SCATT logo`, `Print`, `Preview`, `To be placed at %1m from shooter` |
| `ButtonWithPopup` used by `RangeView` for `View/Filter` toggles | `displayShotlist`, `displaySightingShots`, `displayDeletedShots`, `View.svg` / `View Selected.svg`, `Filter.svg` / `Filter Selected.svg` |

**Dialogs / windows** (`Qt.labs.platform` `FileDialog`, `QtQuick.Dialogs` `ColorDialog`,
`style/Dialog`, `Diagnostics`, `ShowMessageAndQuit`):

| Item | Evidence |
|---|---|
| `SaveFile` / `Save LOG as` dialog | `fileMode`, `nameFilters`, `defaultSuffix`, `acceptLabel`=`Save`, `onAccepted` |
| `importDialog` / `exportDialog` / `reportDialog` | `acceptLabel`, `Import`+`Select file(s) to import from`, `Export`+`Select file to export to`, `Report`+`Select report file name`, `SCATT files (%1)`, `Report (*.cvs)` |
| `ColorDialog` (in `shared/ColorButton`) | `modality=WindowModal`, `showAlphaChannel` |
| `Diagnostics` | `STOP LOG`, `TEST THROUGHPUT`, `Close Diagnostics`, `SaveFile`, `diagnosticMode` |
| `ShowMessageAndQuit` | `textFormat=Text`, `WordWrap`, `qApp.quit` |
| `confirmQuitPopup` | `Are you sure you want to quit application?` + `Cancel`/`Ok` |
| `LanguageSelector` | `ComboBox`, `translations`, `titles`, `modelData`, `Font/DemiBold`, `hintLayout` — a **shared control**, not a screen |

**Keyboard** `[CONFIRMED]`: `Ctrl+Q` quit · `Ctrl+Tab` / `Ctrl+Shift+Tab` next/prev mode ·
`Ctrl+T` toggle maximize range · `Ctrl+1…8` range slots · ShotList keys
(`Home`, `End`, `Return`, `Space`, `Esc`, `Ctrl+A`, `Ctrl+Shift+A`, `Shift+Up/Down`,
`Shift+Home/End`, `PgUp`, `PgDn`, `Ctrl+Up/Down`, `Ctrl+Shift+PgUp/PgDn`, `Alt+Space`,
`Ctrl+Space`).

---

## 3. Main analysis screen structure

### 3.1 Container chain (outermost → innermost)

```
ApplicationWindow "appWindow"                       [CONFIRMED]
  └─ ToolBar header (logo, mode buttons, attention, fullscreen)   [CONFIRMED]
  └─ StackView "stack"
       └─ ShootingViewMode                          [CONFIRMED]
            └─ ShootingView  ⇄ ShootingView_All | ShootingView_Maximized   [CONFIRMED]
                 (Ctrl+T → toggleMaximizedRange; maximizedRange, Window %1 title)  [CONFIRMED]
                 └─ RangeView  =  "layout"          [CONFIRMED]
                      ├─ RangeView_Title            (top strip)
                      ├─ RangeView_TargetView       (center; contains TargetView_SidePane,
                      │                              ShotList, Timeline, Replay, Zoom)
                      ├─ RangeView_Footer           (bottom action bar)
                      └─ RangeView_RegionError      (replaces content when region-locked)
```

`ShootingView_All.qml` is the multi-range layout (`expression for columns`, `RangeView`);
`ShootingView_Maximized.qml` is the single maximized range (`Window %1`).
`RangeView` exposes `enableSidePanel` / `displayPanel` / `displayTarget` / `displayShotlist`
/ `displayTimeline` — **all four regions are independently toggleable** `[CONFIRMED]`.

### 3.2 Region map

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│ HEADER (MainWindow.qml ToolBar)                                                  │
│ [scatt_logo_48px] [mode ToolButton]… [attentionButton ic_report ●blink] [⛶]      │
├──────────────────────────────────────────────────────────────────────────────────┤
│ R1  RangeView_Title   ── top strip ────────────────────────────────────────────  │
│  label/elide  │ BusyIndicator searchIndicator │ sensorSleep │ BatteryIndicator   │
│  [newRangeButton ic_add] [maximizeButton] [closeButton ic_close]   "New window"  │
│  title fmt:  Practice | %1 | %2 | %3 | %4%5     [CONFIRMED]                      │
│              Calibration | %1 | %2 | %3%4       [CONFIRMED]                      │
│              Catalog | %1 | %2 | %3 | %4%5      [CONFIRMED]                      │
│              Select shooter / Select target | %1 / Configure hardware | %1       │
│              + BatteryIndicator: ic_battery_{20..90}_48px, ic_battery_charging_*,│
│                ic_battery_alert_48px, scatt_device_{connected,disconnected}_48   │
│                "Battery charge: %1%", "Charging",                                │
│                "Sensor will shutdown due to inactivity in %1 sec"                │
├──────────────────────────────────────────┬───────────────────────────────────────┤
│ R2  RangeView_TargetView   (CENTER)      │ R3  RangeView_TargetView_SidePane     │
│                                          │       (RIGHT — enableSidePanel)       │
│  ┌────────────────────────────────────┐  │                                       │
│  │ target rendering area              │  │  [component_sidePanel]  [scroll]      │
│  │  SolidBreach / SolidBreachWithText │  │   ├ component_graphs: Chart           │
│  │  TargetScrollIndicator (H/V)       │  │   │   label1 label2 label3 label4     │
│  │  aimingPoint · trace · averagePoint│  │   │   enableDistance / enableCoordina-│
│  │  aiming-zone (Rectangle | Circle)  │  │   │   tion / enableTimeShift / enable-│
│  │  correctionBreach + correctionPulse│  │   │   Speed + pinX + XChartState      │
│  │  homeButton [ic_home]              │  │   │   distanceChartAbsoluteMode       │
│  │  zoomIn · zoomOut · zoomToRing ·   │  │   │   filterCutoff · resampleRate     │
│  │  zoomToFit · userTargetZoomRing    │  │   └ Comments (TextArea + ic_attach)   │
│  │  resultText · timerLabel ·         │  │       "Ballistic ratio"               │
│  │  messageLabel · favoriteButton     │  │       enableShotF · maxShotF          │
│  │  [View|View Selected] [Filter|Filter Selected]  displayShotlist/Sighting/Deleted
│  ├────────────────────────────────────┤  │                                       │
│  │ TRANSPORT (replay)                 │  │  ⇕ enableSidePanel / displayPanel     │
│  │  replayButton [ic_play_arrow|ic_pause│ │                                       │
│  │  stopReplayButton [ic_stop]        │  │                                       │
│  │  replaySlider · replayLabel ·      │  │                                       │
│  │  hintReplayLabel                   │  │                                       │
│  │  "Start replay"/"Pause replay"/    │  │                                       │
│  │   "Resume replay"/"Stop replay"    │  │                                       │
│  ├────────────────────────────────────┤  │                                       │
│  │ SHOTLIST (Table)                   │  │                                       │
│  │  ShotList.qml  — see §3.3 for the  │  │                                       │
│  │  full column enumeration           │  │                                       │
│  └────────────────────────────────────┘  │                                       │
│                                          │                                       │
│  displayTarget / displayShotlist /       │                                       │
│  displayMode ∈ {TargetOnly, TableOnly,   │                                       │
│                 TargetAndTable}          │                                       │
├──────────────────────────────────────────┴───────────────────────────────────────┤
│ R4  RangeView_Timeline   ── bottom ─────────────────────────────────────────────  │
│  firstSegment · lastSegment · segments · offset · duration · pos · size          │
│  sizeX · sizeY · timer · radius · timerEnter · timerStart · timerEnd              │
│  colors literal: lightcoral · skyblue   [CONFIRMED]                               │
│  linked: secondsSinceFirstShot · secondsSinceEnter · secondsToString             │
│  ⇕ displayTimeline                                                                │
├──────────────────────────────────────────────────────────────────────────────────┤
│ R5  RangeView_Footer    ── action bar ──────────────────────────────────────────  │
│  Back · Previous session · Next session                                           │
│  gotoHome · gotoSelectSessionStep · gotoPreviousSession · gotoNextSession         │
│  previousSessionAvailable · nextSessionAvailable · startMatch ("Start Match")     │
│  print [ic_print] · printTargetPopup [ic_pageview] · homeButton [ic_home]         │
│  label · elide                                                                   │
└──────────────────────────────────────────────────────────────────────────────────┘
```

**Proportions:** `[UNKNOWN]` for every dimension. No spacing, width, height, ratio, or
breakpoint is recoverable from bytecode string pools. In particular:

- R1 height, R4 height, R5 height: `[UNKNOWN]`
- R2 : R3 horizontal split (and whether it is a fixed-width pane or a `SplitView`): `[UNKNOWN]`
  — evidence only shows `enableSidePanel` / `displayPanel` as booleans `[CONFIRMED]`.
- Whether the shot list sits *inside* R2 (as drawn above) or spans the full width
  below R2: `[UNKNOWN]`. `displayShotlist` is a sibling of `displayTarget` and
  `displayMode` has a `TargetAndTable` value, which supports the drawn arrangement
  but does not prove the pixel geometry. `[INFERENCE]`
- The literal colours `lightcoral` / `skyblue` in the Timeline are QML named colours
  `[CONFIRMED]` — they sit oddly beside a neutral chrome palette and may be debug-only;
  **treat as `[UNKNOWN]` role** (§6.5).

### 3.3 ShotList — the strongest structural evidence

`ShotList.qml` (lines 2213–2255 attribution; its property pool runs 1849–2213)
is a **column-configurable table**. Every `displayShotList*` property is a *column
visibility toggle*, and it has a matching `shotRow*Width` layout property and a matching
`sizeHint*` sizing property — three-way agreement, which is why these are high-confidence.

| # | Column | `displayShotList*` toggle | Width prop | Size-hint (max text) | Summary/avg prop |
|---|---|---|---|---|---|
| 1 | Hide/restore | — (`enableHiddenShots`) | — | `sizeHintShotRowHide` → `ic_visibility_24px` | — |
| 2 | Shot index | `displayShotListIndex` | `shotRowIndexWidth` | `sizeHintShotRowIndex` → `999` | `indexInSession` |
| 3 | Direction | `displayShotListDirection` | `shotRowDirectionWidth` | `sizeHintShotRowDirection` → direction arrow SVGs | `shotPointDirection` |
| 4 | Result / score | `displayShotListResult` | `shotRowResultWidth` | `sizeHintShotRowResult` → `999.9` | `result` |
| 5 | Aiming time | `displayShotListAimingTime` | `shotRowAimingTimeWidth` | `sizeHintShotRowTime` → `999` | `averageAimingTimeMs` |
| 6 | Hold inside 6 ring (AAP) | `displayShotListHoldInside6aap` | `shotRowHoldWidth` | `sizeHintShotRowHold` → `999%` | `averageHoldInside6aap` |
| 7 | Hold inside 9 ring (AAP) | `displayShotListHoldInside9aap` | `shotRowHoldWidth` | `sizeHintShotRowHold` | `averageHoldInside9aap` |
| 8 | Hold inside 10 ring | `displayShotListHoldInside10` | `shotRowHoldWidth` | `sizeHintShotRowHold` | `averageHoldInside10` |
| 9 | Hold inside 10.5 ring | `displayShotListHoldInside10p5` | `shotRowHoldWidth` | `sizeHintShotRowHold` | `averageHoldInside10p5` |
| 10 | Hold inside 10 ring (AAP) | `displayShotListHoldInside10aap` | `shotRowHoldWidth` | `sizeHintShotRowHold` | `averageHoldInside10aap` |
| 11 | Hold inside 10.5 ring (AAP) | `displayShotListHoldInside10p5aap` | `shotRowHoldWidth` | `sizeHintShotRowHold` | `averageHoldInside10p5aap` |
| 12 | Trace speed | `displayShotListTraceSpeed` | `shotRowSpeedWidth` | `sizeHintShotRowSpeed` → `9999.9` | `averageSpeed` |
| 13 | Trace speed (250 ms) | `displayShotListTraceSpeed250ms` | `shotRowSpeedWidth` | `sizeHintShotRowSpeed` | `averageSpeed250ms` |
| 14 | Breach from AAP | `displayShotListBreachFromAAP` | `shotRowBreachFromAAPWidth` | `sizeHintShotRowBreachFromAAP` | `averageDistanceBreachFromAAP` |
| 15 | Favorites | `displayShotListFavorites` | `shotRowFavoritesWidth` | `sizeHintShotRowFavorites` → `Favorites.svg` | `favoriteShotCount` |

All `displayShotList*` names: `[CONFIRMED]` (lines 1541–1554).
All `shotRow*Width` / `sizeHint*` / `average*` names: `[CONFIRMED]` (lines 1869–2212).
**The 1:1 correspondence is `[INFERENCE]`** — but it is the standard QML idiom
(toggle → column width → delegate size hint) and all three sets line up exactly.

**Row types** `[CONFIRMED]` (`rowType` / `SerieListItem` and the enum strings):

```
SightingsTitleRow → SightingsTargetRow          (sighting block header + target row)
SerieTitleRow     → SerieTargetRow              ("Series %1" header + target row)
ShotDescriptionRow                              (per-shot detail)
ShotRow                                        (the table row above)
SerieSummaryRow                                 (per-series summary)
SessionSummaryRow                               (whole-session summary)
deletedShotRowDelegate → restoreButton [ic_replay]   (deleted shots)
```
Special rows carry `isTotalsRow`, `stat`, `StatShots`, `descriptor`.
Title-row literals: `Sighting` · `Target` · `Serie` · `Shot index` · `Score` ·
`Deleted shot` · `Aiming trace speed (control interval) (mm/s)` ·
`Aiming trace speed (250 ms) (mm/s)` `[CONFIRMED]`.

**Row metrics** `[CONFIRMED]`: `shotRowHeight`, `shotRowCellHeight`, `cellLeftRightPadding`,
`cellTopBottomPadding`, `serieTitleRowHeight`, `descriptorRowHeight`,
`summaryRowHeight`, `summaryRowCellHeight`, `shotRowHideWidth`, `sizeHintSerieTitleRow`.
**Actual numeric values: `[UNKNOWN]`.**

**Target-view coupling** (what selecting a row does) `[CONFIRMED]`:
`selectShot`, `selectPreviousShot`/`selectNextShot` (+ page variants), `selectFirstShot`,
`selectLastShot`, `selectAllShots`, `deselectAllShots`, `invertSelection`,
`positionViewAtCurrentShot`, `itemSelected`, `targetDoubleClicked`, `traceSelection`,
`startReplay`, `toggleReplay`, `replayActive`, `stopReplay`,
`itemDelegate` (hover → `ToolTip` with `delay`/`timeout`),
`actionDelete`/`actionHide` + `Delete shot(s)`/`Undelete shot(s)`/`Hide shot(s)`/`Unhide shot(s)`,
`selectionShotCount`, `selectionDeletedShotCount`, `selectionSightingShotCount`,
`selectionMatchShotCount`, `selectionHiddenShotCount`.

**View-mode triple** `[CONFIRMED]`: `displayMode` ∈ `TargetOnly` | `TableOnly` | `TargetAndTable`
(plus `TargetOnly`'s sibling string `Deleted`, `Table only`, `Target and table`,
`Target only` — the UI labels for the same enum).

**TargetView overlays** (inside R2) `[CONFIRMED]`:
`SolidBreach` with `correctionBreach` / `correctionPulseTimer` /
`waitingForTargetExit` / `averageAimingPoint` / `boundsCircle` /
`defaultTraceThickness` / `traceObject` / `firstIndex` / `lastIndex` / `resampled` / `aap`;
`TargetScrollIndicator` with `orientation`, `bounds`, `targetItem`, `penWidth`, `trace`;
zoom: `finalZoomLevel`, `ringFromZoom`, `minimumZoomLevel`, `fixedCenter`, `updateZoom`,
`timerUpdateZoom`, `onUserChangedZoom`, `enableAnimation`, `Behavior/PropertyAnimation`,
`restart`, `OutQuart`, `pressedButtons`, `mousePosMm`, `correctionPoint`.

### 3.4 Side pane (R3)

`RangeView_TargetView_SidePane.qml` (2868–2896) `[CONFIRMED]`:

- **`component_sidePanel` + `scroll`** — it is a scrollable pane.
- **Four charts**, each a `Chart` with its own `component_*`, `pin*` and `*ChartState`:
  `component_distance`, `component_coordination`, `component_timeShift`, `component_speed`
  with `distanceGraph`/`enableDistance`, `coordinationGraph`/`enableCoordination`,
  `timeShiftGraph`/`enableTimeShift`, `speedGraph`/`enableSpeed`
  `[CONFIRMED]` (property names appear in the SettingsEditor pool at 1571–1574 and the
  SidePane pool at 2838–2867).
- **Chart controls**: `slider` + `cutoff` + `resample rate`,
  `distanceChartAbsoluteMode`, `timeShiftChartWithDecimalsMode`,
  `filterCutoff`, `resampleRate`, `enableShotF`, `maxShotF`
  `[CONFIRMED]`.
- **Labels**: `label1`…`label4` (one per chart) `[CONFIRMED]`.
- **Comments block**: `TextArea edit` + `placeholderText` + `onEditingFinished` +
  `onTabPressed`, `Flickable`, `VerticalFlick`, `escapedCommentsString`,
  attach icon `ic_attach_file_48px.svg`, heading `Comments`, `Ballistic ratio`
  (`absolute` / `with decimals`) `[CONFIRMED]`.

### 3.5 Region error state

`RangeView_RegionError.qml` (2556–2703) `[CONFIRMED]` — a **blocking substitute for the
screen content**, not an overlay:

- `regionErrorCisOnlyF` — "This device is for CIS market only. / Please switch to Russian language."
- `regionErrorChina` — "This device is not authorized for sale in China/Taiwan/Hong-Kong. / Please switch to another language."
- "This device is not authorized for use with this language."
  `[CONFIRMED]`

Trigger: `onRegionErrorChanged` in `RangeView` `[CONFIRMED]`.
**STASYS has no region-lock requirement** → the *pattern* (a full-screen explanatory
substitution state with one corrective action) is reusable for fatal device states; the
content is not. `[INFERENCE]`

---

## 4. Screen inventory & workflows

### 4.1 Inventory

| File (`qrc:///qml/…`) | Class | Purpose | Key widgets / strings present | Trigger |
|---|---|---|---|---|
| `main.qml` | entry | boot, create window | `ApplicationWindow`, `appWindow` | process start `[CONFIRMED]` |
| `MainWindow.qml` | **chrome** | header, mode stack, quit/job overlays | `ToolBar`, `StackView stack`, logo, `ImageToolButton attentionButton` (`ic_report`), `fullScreenButton`, `modeTitle`, `confirmQuitPopup`, `ProgressBar` job overlay, `Ctrl+Tab` | always `[CONFIRMED]` |
| `ShootingViewMode.qml` | **mode** | shell that feeds a `RangeView` its data | `RangeData range`, `displayMode`, `shotListModel`, `Session`, `selectedShot`, `TargetDescriptor`, `resultDecimals`, `speedDecimals`, `currentShotIndexInSerieDisplay`, `currentSerieShotCount` | mode = Shooting `[CONFIRMED]` |
| `SettingsEditorMode.qml` | **mode** | grouped settings form | `ControlScrollView`, `GroupBox`, `GridLayout columns`, `LanguageSelector`, `FontButton`, `CheckBox`, `RadioButton`, `SpinBox`, `DoubleSpinBox`, `ColorButton`, `ButtonWithConfirmPopup` + ~60 labels (§4.2) | `gotoSettings` / `Preferences` `[CONFIRMED]` |
| `AboutMode.qml` | **mode** | version + credits | `%1 version %2`, `applicationVersion`, `gitDateTime`, `gitCommit`, "Check for support and updates \<a href…\>", "Copyright 1993-%1 SCATT Electronics, LLC. All rights reserved." | `gotoAbout` / `About` `[CONFIRMED]` |
| `Diagnostics.qml` | **dialog** | device log/throughput | `STOP LOG`, `TEST THROUGHPUT`, `Close Diagnostics`, `SaveFile`, `Save LOG as`, `VerticalBar`, `diagnosticMode`, `MouseArea counter` | `gotoDiagnistics` + `attentionNeeded` `[CONFIRMED]` |
| `ShowMessageAndQuit.qml` | **dialog** | fatal message then exit | `Text WordWrap`, `qApp.quit`, `colors.windowText` | unrecoverable error `[CONFIRMED]` |
| `LanguageSelector.qml` | **shared control** | language picker | `ComboBox`, `translations`, `titles`, `hintLayout`, `Font/DemiBold` | embedded in Settings `[CONFIRMED]` |
| `MacOSMenuBar.qml` | platform | macOS menu bar | `MenuBar/Menu/MenuItem`, `about.*`, `preferences`, `gotoAbout`, `gotoSettings`, `Quit` | macOS only `[CONFIRMED]` |
| `ShootingView.qml` | window mgr | one window per range, maximization | `toggleMaximizedRange` `Ctrl+T`, `Ctrl+1…8`, `maximizedRange`, `ShootingView_All`, `ShootingView_Maximized`, `Window %1` | mode = Shooting `[CONFIRMED]` |
| `ShootingView_All.qml` | layout | N ranges side by side | `RangeView`, `expression for columns` | >1 range `[INFERENCE]` |
| `ShootingView_Maximized.qml` | layout + calibration overlays | single max range; sensor preview | `componentPreviewHint`, `componentPreviewImage` `PreviewImage`, `clipCircle`, `rotate`, `ic_videocam_black_48px`, `componentPreviewShotImage` `ic_photo_camera_black_48px`, `componentCalibrationTarget`, `calibrationTarget`, `diameter`, `sensitiveDiameter`, `Translate/Scale`, `calibrationShots`, `calibrationCursor` | maximize `[INFERENCE]` |
| `RangeView.qml` | **screen container** | composes R1–R5, owns state switches | `layout`, `BusyIndicator searchIndicator`, `sensorSleep`, `BatteryIndicator`, `newRangeButton ic_add`, `maximizeButton isMaximized`, `closeButton ic_close`, `"New window"`, all step/title strings, `UndefinedMode`, `regionError` | always (within mode) `[CONFIRMED]` |
| `RangeView_Title.qml` | **R1** | top strip | `battery`, `chargeIcon(s)`, battery icon ladder, `scatt_device_{connected,disconnected}` | always `[CONFIRMED]` |
| `RangeView_TargetView.qml` | **R2** | target + transport + table host | `contents`, `placeholder`, `children`, `homeButton ic_home` | always `[CONFIRMED]` |
| `RangeView_TargetView_SidePane.qml` | **R3** | charts + comments | 4 `Chart`s, `Comments`, `Ballistic ratio`, `ic_attach_file` | `enableSidePanel` `[CONFIRMED]` |
| `RangeView_Timeline.qml` | **R4** | shot/trace timeline | `firstSegment`…`segments`, `lightcoral`, `skyblue` | `displayTimeline` `[CONFIRMED]` |
| `RangeView_Footer.qml` | **R5** | actions | `Back`, `Previous session`, `Next session`, `startMatch`, `print`, `homeButton` | always `[CONFIRMED]` |
| `ShotList.qml` | **table** | full shot table | §3.3 | `displayShotlist` `[CONFIRMED]` |
| `BatteryIndicator.qml` | widget | charge + connection | icon ladder + `Battery charge: %1%` | always `[CONFIRMED]` |
| `TargetGridSelector.qml` | selector | grid of targets | `GridView`, `desiredCellWidth`, `minCellSize`, `cellSize`, `margins`, `round`, `Outline`, `focusPressedColor`, `delegatePressedColor` | SelectTarget, `targetListAsGrid=true` `[CONFIRMED]` |
| `TargetListSelector.qml` | selector | list of targets | `ListView`-style `delayed`, `onHighlightedChanged`, `Keys`, `filteredTargets`, `indexOf`, `Key_Home`, `Key_End` | SelectTarget, grid off `[CONFIRMED]` |
| `shared/TargetComboBoxSelector.qml` | selector | compact target dropdown | `showInvisible`, `selection`, `targetDoubleClicked`, `allTargets`, `targets` | compact contexts `[INFERENCE]` |
| `RangeView_PracticeMode_SelectShooterStep.qml` | **P1** | pick/create shooter | `AddShooterPopup`, `onShooterAdded`, `scatt_ic_person_48px`, `"No shooter"` | `gotoSelectShooterStep` `[CONFIRMED]` |
| `RangeView_PracticeMode_ConfigureHardwareStep.qml` | **P2** | connect sensor | `"Connect the sensor via:"`, `ic_usb_48px`, `ic_signal_wifi_4_bar_48px`, `"No devices"`, `listDevices`, `connectDevice`, `deviceInUse`, `"The device firmware is outdated…"`, `"This device is already used in another window"`, `gotoSelectShooterStep`, `gotoSelectTargetStep` | from P1 `[CONFIRMED]` |
| `RangeView_PracticeMode_SelectTargetStep.qml` | **P3** | pick target | `gridComponent TargetGridSelector`, `listComponent TargetListSelector`, `Flow`: `distanceFlow`/`caliberFlow`/`tagsFlow`, `ic_view_module_black_48px`, `ic_view_list_black_48px`, `Slider snapMode SnapAlways`, `PrintTargetPopup`, `Caliber`, `Grid view`, `List view`, `Print target`, `Continue`, `targetListAsGrid`, `targetGridCellWidth`, `gotoConfigureHardwareStep`, `gotoCalibrationStep` | from P2 `[CONFIRMED]` |
| `RangeView_PracticeMode_CalibrationStep.qml` | **P4** | sensor calibration | `Vision`, `Preview mode`, `Shot sensitivity`, `Max/Min sensitivity`, `Ultra sensitive mode`, `Filter foreign shots`, `Clear target`, `Back to Shooting`, `cancelCalibration`, `clear`, `acceptCalibration`, `checkboxPreviewMode` + long hint text | from P3 `[CONFIRMED]` |
| `RangeView_PracticeMode_ShootingStep.qml` | **P5** | live shooting | `Stop practice`, `Make correction`, `Calibration`, `"Are you sure you want to restart session?"`, `New session`, `correctionAllowed`, `correctionMode`, `toogleCorrection`, `liveMatchMode` | from P4 `[CONFIRMED]` |
| `RangeView_CatalogMode_SelectSessionStep.qml` | **C1** | browse saved sessions | `listShooters`, `listSessions`, `checkboxAllSessions` (tristate), `Shooters`, `Practices`, `Import`/`Export`/`Report`/`Delete`/`Open`, `"%n shot(s)"`, `summaryShotCount`, `gotoSessionViewStep`, `gotoHome` | `gotoCatalogMode` `[CONFIRMED]` |
| `RangeView_CatalogMode_SessionViewStep.qml` | **C2** | review one session | `RangeView_Title`, `RangeView_TargetView`, `mainTarget`, `HorizontalBar`, `RangeView_Footer`, `Back`, `gotoPreviousSession`, `gotoNextSession` | from C1 `[CONFIRMED]` |
| `RangeView_UndefinedMode.qml` | **home** | launcher | `newPracticeButton` `scatt_start_new_practice_hc_96px`, `catalogButton` `scatt_open_file_hc_96px`, `"Start new practice"`, `"Open recent sessions"`, `gotoPracticeMode`, `gotoCatalogMode`, `AlignCenter` | mode = undefined `[CONFIRMED]` |
| `RangeView_RegionError.qml` | **state** | region-lock block | §3.5 | `regionError` set `[CONFIRMED]` |
| `RangeView_State_debug.qml` | debug | live packet state | `packet*`, `PREVIEW`, `TEMPLATE`, `MatrixImage`, `ADJUST`, `MAIN`, `EMULATION`, `opticalCenter`, `frameSize` | `debugBuild` `[CONFIRMED]` |
| `RangeView_Emulator_debug.qml` | debug | shot emulation | `Emulator`, `emulationTarget`, `zoomLevel`, `debug_emulation*`, `random`, `Ctrl+Space`, `Alt+Space` | `debugBuild` `[CONFIRMED]` |

### 4.2 Settings editor groups (from `SettingsEditorMode.qml` pool, lines 1389–1578)

All labels `[CONFIRMED]`; grouping into `GroupBox`/`GridLayout columns=…` `[CONFIRMED]`.

| Group | Controls / labels |
|---|---|
| **General** | `Language` (`LanguageSelector`), `Enable auto replay`, `Exit target for auto replay`, `Auto zoom`, `Fixed target center`, `Play shot sound`, `Pronounce the score`, `Ask for confirmation when closing the program` (`ButtonWithConfirmPopup`), `FontButton selectedFont`, `ColorButton` |
| **Power supply** | `Power supply frequency` + `Auto` / `50 Hz` / `60 Hz`; help: "Some types of lamps may cause excessive flickering.", "To improve sensor performance please select the power frequency corresponding to your region.", "You need to restart practice session(s) to apply the change." |
| **Aiming trace** | "How many seconds of the aiming trace to record" `before the shot` / `after the shot`, `Limit display of aiming trace`, "Calculations interval before shot" (`traces` / `charts`), `Auto replay delay` (`DoubleSpinBox`) |
| **Aiming zone** | `Aiming zone`, `Display average aimpoint`, `Display average shot coordinate`, `Display aiming zone`, shape `Rectangle` / `Circle` |
| **Shot list** (column toggles) | `Shot list` heading + all 15 `displayShotList*` labels: `Shot index#`, `Shot orientation relative to center`, `Shot score`, `Aiming time`, "Ratio of hold inside 6 ring diameter centered on average aimpoint", "…9 ring…", "Ratio of hold inside 10 ring", "Ratio of hold inside 10.5 ring", "Ratio of hold inside 10 ring diameter centered on average aimpoint", "Ratio of hold inside 10.5 ring diameter centered on average aimpoint", "Aiming trace speed (calculations interval for traces)", "Aiming trace speed (250 ms)", "Distance between average aimpoint and breach", `Favorites` |
| **Colors** | `Colors` heading + `Target background`, `Target 'White'`, `Target 'Black'`, `Shot`, `Shot border`, `Selected shot`, `Selected shot border`, `Aimpoint`, `Trace`, `Trace 1 sec before shot`, `Trace 0.3 sec before shot`, `Follow through trace`, `Average point`, `Distance`, `Coordination`, `Time shift`, `Average trace speed` — each with a `ColorButton` |
| **Reset** | `Defaults`, `Reset`, `Reset storage`, "Are you sure you want to permanently delete all data?" (`ButtonWithConfirmPopup`) |

Storage keys for settings `[CONFIRMED]` (`strings_ui.txt`):
`colors/targetBackground`, `colors/targetBlack`, `colors/targetWhite`,
`colors/aimingPoint`, `colors/traceBeforeShot`, `colors/traceAfterShot`,
`appearance/targetGridCellWidth`, `appearance/targetListAsGrid`,
`window/x|y|width|height|visibility`, `shooters/default`, `targets/tags1|tags2`,
`targets/<uuid>/target|shooter_name|target_uuid|shots`, `calibration/`.

> Note the persisted colour key set is **6 keys, not 17** — `colors/breach`,
> `colors/activeBreach`, `colors/targetBackground` etc. appear as *property* names
> in QML but only 6 are `QSettings` keys. `[CONFIRMED]` — do not assume all colour
> roles persist.

### 4.3 Core workflows (start → finish)

**W1 — New practice (primary):**
home (`RangeView_UndefinedMode`) → *Start new practice* → `gotoPracticeMode`
→ **P1** pick shooter (`AddShooterPopup` if none) → **P2** connect sensor
(USB or Wi-Fi, device list, firmware warning) → **P3** pick target
(grid/list toggle, filter by distance/caliber/tag, optional *Print target*) →
**P4** calibrate (preview mode, sensitivity, filter foreign shots, *Clear target*,
accept/cancel) → **P5** shoot → shots land in `ShotList` + target view + timeline →
*Stop practice* / *New session* (with restart confirm) → session persisted.
`[CONFIRMED]` for every step name, edge and label.

**W2 — Review a session (catalog):**
home → *Open recent sessions* → `gotoCatalogMode` → **C1** choose shooter(s) +
session(s) with tristate checkboxes, optional Import/Export/Report/Delete →
`gotoSessionViewStep` → **C2** full analysis screen with `Back` / `Previous session` /
`Next session` → `gotoHome`.
`[CONFIRMED]`

**W3 — Analyze one shot:** click a `ShotRow` (`selectShot`) → target view highlights the
breach + trace (`SolidBreach`, `traceSelection`), side-pane charts recompute,
`positionViewAtCurrentShot` scrolls the list; `favoriteButton` toggles favorite;
right-click/delete hides (`Hide shot(s)` → `deletedShotRowDelegate` + restore button).
`[CONFIRMED]`

**W4 — Replay:** `replayButton` → `startReplay`/`toggleReplay`; states `Start replay` /
`Pause replay` / `Resume replay`; `replaySlider` scrubs `replayPosition`;
`stopReplayButton` → `stopReplay`; optional auto-replay (`autoReplayEnabled`,
`autoReplayDelay`, `exitTargetForAutoReplay`) with `waitingForAutoReplay`.
`[CONFIRMED]`

**W5 — Adjust the view:** `View` toggle cycles `displayMode` among
`Target only` / `Table only` / `Target and table`; `Filter` toggles
`displaySightingShots` / `displayDeletedShots`; `enableSidePanel` shows/hides R3;
`displayTimeline` shows/hides R4; zoom `zoomIn`/`zoomOut`/`zoomToRing`/`zoomToFit`.
`[CONFIRMED]`

**W6 — Settings / About / Diagnostics:** header `mode` buttons or `Ctrl+Tab`;
`Preferences` → scrollable `GroupBox` form (§4.2); `About` → version block;
attention button (`ic_report`, pulsing `SequentialAnimation`) → `Diagnostics`.
`[CONFIRMED]`

---

## 5. Widget map: SCATT → STASYS

STASYS components are quoted with `core.py` line numbers from the current working tree.

### 5.1 Shared widgets

| SCATT widget (`qml/shared/`) | Evidence of role | Nearest STASYS target | Verdict |
|---|---|---|---|
| `Icon` | `source`, `imageHeight` | `QLabel`+`QPixmap` / `QIcon` helper in `_stylized_button` (`core.py:3139`) | **NEW WIDGET** — `_icon(name, size, tint)` helper; SCATT's `Icon` also carries the recolouring role |
| `ImageToolButton` | `tooltipTimeout`, `iconSize`, used for header buttons | `QPushButton` via `_stylized_button` (`core.py:3139`) | **NEW WIDGET** — `IconButton(QPushButton)` with icon-only mode + tooltip delay |
| `ImageToolButtonWithPopup` / `WithConfirmPopup` | `popupVisible`, `tooltipTimeout` | — | **NEW WIDGET** — `IconButton.menu` / `.confirm` variants |
| `MyLabel` | base label (`hugeFont` declared on `HugeLabel`) | `QLabel` styling scattered across `core.py` | **NEW WIDGET** — `Label` base with `role=` |
| `HugeLabel` | `hugeFont` | — | **NEW WIDGET** — role `huge` (see §5.4 scale) |
| `LargeLabel` | `largeFont` | — | **NEW WIDGET** — role `large` |
| `NormalLabel` | `HugeFont` declared in its pool | — | **NEW WIDGET** — role `normal` |
| `SmallLabel` | — | — | **NEW WIDGET** — role `small` |
| `MyTabButton` | extends `TabButton`; literals `#c2c2c2`, `#33333333` | `QTabBar::tab` stylesheet (`core.py:3229-3260`) | **REUSE + restyle** — keep `QTabWidget`, restyle tab chrome; do not rebuild |
| `ButtonWithPopup` | `popupVisible`, hex block `#0066ff/#ffffff/#26282a/#353637/#cce0ff/#f0f6ff/#d0d0d0/#e0e0e0` | — | **NEW WIDGET** — `MenuButton` (primary + ▾ split) |
| `ButtonWithConfirmPopup` | `acceptText` | — | **NEW WIDGET** — `ConfirmButton` |
| `ConfirmPopup` | `messageText`, `acceptButton`, `rejectText`, `rejectButton` | `QMessageBox` ad-hoc | **NEW WIDGET** — `ConfirmPopup(QDialog)`; replaces ad-hoc `QMessageBox` calls |
| `AddShooterPopup` | `Add shooter`, `Name`, `Name already exists` | — | **NEW WIDGET** — `NameDialog` |
| `PrintTargetPopup` | `Print target - %1`, print options, `Print`/`Preview` | — | **NEW WIDGET** — optional; only if STASYS gains printable targets. Slot otherwise unmapped |
| `EnumComboBox` | `enumModel`, `currentEnumValue`, `enumTranslations`, `values` | `QComboBox` (e.g. `core.py:3861`) | **NEW WIDGET** — `EnumComboBox(QComboBox)` fed by Python `Enum` |
| `DoubleSpinBox` | `realFrom`, `realTo`, `decimals`, `stepSize`, `initRealValue`, `onRealValueChanged` | `QDoubleSpinBox` | **REUSE + restyle** — add `initRealValue` (write-once init so loading settings doesn't loop) |
| `ColorButton` | `ColorDialog`, `modality=WindowModal`, `showAlphaChannel` | — (no colour picker today) | **NEW WIDGET** — `ColorButton(QPushButton)` swatch + `QColorDialog`; **required** for §6 colour settings |
| `FontButton` | `currentFont`, `familiesList/stylesList/sizesList`, "The Quick Brown Fox…" | — | **NEW WIDGET** — low priority (STASYS has no font setting today) |
| `HorizontalBar` | referenced by `SessionViewStep` (`line 2388`) | — | **NEW WIDGET** — horizontal meter/gauge. **Exact purpose `[UNKNOWN]`** |
| `VerticalBar` | used by `Diagnostics` next to `MouseArea counter` | — | **NEW WIDGET** — vertical meter. `[INFERENCE]` a level/throughput gauge in diagnostics |
| `SolidBreach` | `correctionBreach`, `pulse`, `correctionPulseTimer`, `center`, `selected`, `deleted` | impact marker drawn inside `AimCanvas` (`core.py:2092`) | **ABSORB** — fold into `AimCanvas._draw_*` rather than a separate widget |
| `SolidBreachWithText` | `minimumPointSize`, `fontSizeMode=Fit`, `caliber`, `center`, `selected`, `deleted` | — | **NEW WIDGET** — `ScoredMarker` (breach dot + fitted score label); call from `AimCanvas` |
| `TargetScrollIndicator` | `orientation` (H/V), `bounds`, `scrollPosition`, `zooming`, `targetSize`, `barSize` | — | **NEW WIDGET** — scroll/zoom indicator overlay for `AimCanvas` |
| `TargetComboBoxSelector` | `showInvisible`, `selection`, `targetDoubleClicked`, `allTargets` | `cmb_target_type` (`core.py:3861`) | **REUSE + extend** — add target thumbnails / double-click-to-select |
| `ControlScrollView` | `focusedItem`, `focusedTextItem`, `cursorRectangle`, `forceChildVisible`, `vscrollbar/hscrollbar` | `QScrollArea` | **NEW WIDGET** — `FocusScrollArea`: auto-scrolls to the focused child in the Settings form |
| `FocusSpy` | `onActiveFocusChanged`, `activeFocusControl` | — | **NEW WIDGET** — small; pair with `ControlScrollView` |
| `Icon` (used as `source`/`imageHeight`) | see above | — | — |

### 5.2 RangeView parts

| SCATT region | Evidence | STASYS target | Verdict |
|---|---|---|---|
| `RangeView_Title` (R1) | `label/elide`, `BusyIndicator searchIndicator`, `sensorSleep`, `BatteryIndicator`, `newRangeButton`, `maximizeButton`, `closeButton` | header `QFrame` (`core.py:3212`) + `lbl_session_info` (`core.py:3221`) | **MERGE** — SCATT's per-range title strip folds into STASYS's single global header |
| `BatteryIndicator` | icon ladder + `Battery charge: %1%` | — | **NEW WIDGET** — only if a battery-powered sensor is added; otherwise omit. Slot `[UNKNOWN]` need |
| `RangeView_TargetView` (R2) | `contents/placeholder/children`, `homeButton`, transport, view/filter toggles, zoom | `AimCanvas` (`core.py:2092`) | **REUSE** `AimCanvas` as the target pane; add SCATT's zoom/`homeButton` chrome around it |
| `RangeView_TargetView_SidePane` (R3) | 4 charts + `Comments` + `Ballistic ratio` | `SparklineWidget` (`core.py:2777`), `SessionStatsWidget` (`core.py:2984`) | **PARTIAL** — side pane container is **NEW**; content = existing `SparklineWidget`/`SessionStatsWidget` promoted into it. The 4 named charts (Distance / Coordination / Time shift / Speed) are **NEW** if STASYS wants parity |
| `RangeView_Timeline` (R4) | `segments`, `timerEnter/Start/End`, `displayTimeline` | `ReplayBar` (`core.py:2637`) | **MERGE** — `ReplayBar` occupies R4; SCATT's segment/timeline ruler becomes an added widget inside it |
| `RangeView_Footer` (R5) | `Back`, `Previous/Next session`, `startMatch`, `print`, `homeButton` | `bottom_strip` in Training tab (`core.py:3790`) | **NEW WIDGET** — `FooterBar(QFrame)`: a real footer row, currently missing from STASYS |
| `ShotList` | §3.3 | `ShotFilmStrip` (`core.py:2901`) + `ShotChip` (`core.py:2839`) | **COEXIST** — `ShotFilmStrip` stays as a compact strip; the **full column table is NEW** (`ShotTable(QTableView)`) |
| `TargetGridSelector` | `GridView`, `desiredCellWidth`, `minCellSize`, `cellSize`, `margins` | — | **NEW WIDGET** — `TargetGridWidget` (part of the P3 wizard) |
| `TargetListSelector` | `filteredTargets`, `Key_Home/End` | — | **NEW WIDGET** — `TargetListWidget` (same wizard, list mode) |
| `RangeView_RegionError` | 3 region messages | — | **PATTERN ONLY** — implement as `FatalStatePage(QFrame)` for device-fatal states; no region lock in STASYS |
| `RangeView_UndefinedMode` (home) | `Start new practice` / `Open recent sessions` 96px cards | `ConnectionScreen` (`core.py:1188`) | **EXTEND** `ConnectionScreen` — add the two big launcher cards |
| `RangeView_State_debug` / `Emulator_debug` | `packet*`, `EMULATION` | — | **OMIT** — developer-only; out of scope for a reskin |
| Wizard steps P1–P5, C1–C2 | §4.1 | — | **NEW** — see §8.5 |

### 5.3 Screen → tab mapping (the explicit contract)

STASYS currently has 5 tabs registered at `core.py:3300, 3490, 3661, 3806, 4166`.

| STASYS tab | Line | Fate | Rationale |
|---|---|---|---|
| **Shot Analysis** | `3300` | **SURVIVES — becomes the SCATT main screen (R1–R5)** | This is the analysis-first landing page; SCATT's `RangeView` is exactly that screen. Grow it into the 5-region layout. |
| **Legacy Detection** | `3490` (already `setTabVisible(…, False)`) | **STAYS HIDDEN → later REMOVED** | Already invisible; it holds backend-compat widgets (`core.py:3297` comment). Do not reskin it. |
| **History** | `3661` | **SURVIVES — becomes SCATT `CatalogMode` (C1/C2)** | Session browser + filmstrip + detail maps directly to SelectSessionStep/SessionViewStep. Keep `QSplitter` (`core.py:3531`). |
| **Training** | `3806` | **MERGES into Shot Analysis** | SCATT has *one* shooting screen, not separate "analysis" vs "live" screens. The live `AimCanvas` + `CALIBRATE`/`TARE` strip becomes Shot Analysis's center region in live mode. **Recommendation:** delete the tab, keep the widgets. |
| **Settings** | `4166` | **SURVIVES — becomes SCATT `SettingsEditorMode`** | Restructure into `GroupBox` sections per §4.2; `LanguageSelector` slot maps to a language combo if STASYS ever localizes. |

**Net result: 4 tabs → 4 tabs** (Shot Analysis / History / [wizard entry] / Settings),
with Training folded away. A fifth entry — **New Practice wizard** — is recommended as
either a tab or a modal flow launched from the home card; which is `[UNKNOWN]` and is
an open product decision, recorded as such rather than guessed.

SCATT modes that have **no** STASYS tab: `AboutMode` (add to header menu or Settings
footer), `Diagnostics` (add as a header popup, matching SCATT's `attentionButton`).
`[INFERENCE]`

### 5.4 Label type scale (SCATT → STASYS)

SCATT declares 5 label sizes (`HugeLabel`/`LargeLabel`/`NormalLabel`/`SmallLabel`/`MyLabel`)
`[CONFIRMED]` as files, with `hugeFont`/`largeFont`/`HugeFont` property names
`[CONFIRMED]`. **SCATT's actual pixel/point values: `[UNKNOWN]`.**
STASYS must define its own scale, harmonised with sizes already used in `core.py`
(observed: 40 px display numbers `core.py:3345`, 32 px `core.py:3574`, 24 px titles
`core.py:3201/3823`, 16 px values `core.py:3047`, 14 px card titles `core.py:3006`,
13 px body `core.py:3167`, 12 px `core.py:1212`, 11 px captions `core.py:3019`,
10 px section labels `core.py:3328`, 9 px micro `core.py:3042`).

| SCATT label | STASYS role | Suggested size | Colour |
|---|---|---|---|
| `HugeLabel` | hero numbers, mode headings | 32–40 px | `text_primary` |
| `LargeLabel` | card/section title | 16 px, 600 | `text_primary` |
| `NormalLabel` | body / control label | 13 px | `text_primary` |
| `MyLabel` | default | 13 px | `text_primary` |
| `SmallLabel` | caption / hint | 11 px | `text_secondary` |
| *(SCATT has none — add)* | section eyebrow (uppercase, tracked) | 10 px, 700, `letter-spacing:1px` | `text_muted` |

The last row matches STASYS's existing idiom (`core.py:3328, 3341, 3360`) — **keep it**;
it is STASYS's own, not a SCATT import. `[INFERENCE]`

---

## 6. Palette mapping (the reskin contract)

### 6.1 Is SCATT light or dark? — the determination

**Answer: SCATT is a LIGHT-themed application with a dark GRAPHICS subsystem.**

Confidence: **`[INFERENCE]` — high**, converging from four independent lines:

1. **The three surviving literal hex colours in `MyTabButton`** `[CONFIRMED]`:
   `#c2c2c2` (a light-medium grey — an outline/underline that only reads on white)
   and `#33333333` (a **20 % black** scrim). A dark theme would use a light scrim.
2. **`ShowMessageAndQuit` binds `colors.windowText`** `[CONFIRMED]` — so `windowText`
   is a *real* palette role alongside `windowBackground`, not an incidental name.
   A theme with a distinct `windowText` role bound to `Text` is a text-on-surface theme.
3. **Colour *storage* key set** `[CONFIRMED]` (`strings_ui.txt`) is
   `targetBackground`, `targetWhite`, `targetBlack`, `aimingPoint`, `traceBeforeShot`,
   `traceAfterShot` — **no `windowBackground` key**. The window chrome colour is therefore
   *not user-persisted*, i.e. it is a fixed, baked-in theme constant.
4. **No dark-theme marker exists anywhere.** `grep` for `Palette`, `windowBackground`,
   `dark` across the exe returns only the QML property references — there is no
   `Material.Dark`, no `palette.dark`, no `theme=dark` string `[CONFIRMED]` by absence.

**What is genuinely `[UNKNOWN]`:** the *values* of `windowBackground` and `windowText`.
They are C++-side `QColor`s and appear as **zero** UTF-16 hex literals in `scattbasic.exe`
(my first scan reported 28 hits; that was a malformed regex artifact and is retracted —
a corrected scan of properly-aligned UTF-16LE runs returns **0** hex literals).
The only hex literals present are the 11 QML literals above plus SVG fills.
**Do not invent SCATT hex values.**

**Consequence for this project:** SCATT being light does **not** mean STASYS goes light.
The brief is explicit that STASYS keeps its dark palette. What we import from SCATT is
*layout and workflow*, and its **semantic colour roles** — mapped onto STASYS's dark
values below.

### 6.2 Identified SCATT colour roles

`[CONFIRMED]` as identifiers unless noted.

**A. Chrome roles** (QML property references; values `[UNKNOWN]`):
`windowBackground` · `windowText`

**B. Target-graphic roles** — QML properties `[CONFIRMED]` **and** `QSettings` keys
`[CONFIRMED]`: `targetBackground` · `targetWhite` · `targetBlack` · `aimingPoint` ·
`traceBeforeShot` · `traceAfterShot`

**C. Target-graphic roles** — QML properties `[CONFIRMED]`, **no** settings key:
`breach` · `breachBorder` · `activeBreach` · `activeBreachBorder` · `trace` ·
`traceAfterShot` · `averagePoint`

**D. Chart/graph roles** `[CONFIRMED]`: `distanceGraph` · `coordinationGraph` ·
`timeShiftGraph` · `speedGraph` (+ `labelsColor`, `labelsVisible`, `labelsFont`)

**E. `TargetElementColor` / `RenderColorMode`** — **`[UNKNOWN]`, and I could not locate
either string in the extracted evidence or via direct read-only `grep` of
`scattbasic.exe`** (0 hits). They were named in the task brief but do not appear in
`strings_utf16.txt`, `strings_ui.txt`, `resource_paths.txt`, or the exe's string table.
Nearest confirmed relatives: `TargetElement`/`TargetDescriptor`/`TargetBackgroundItem`
`[CONFIRMED]` (C++ types), and `displayAimingZoneType` ∈ `Rectangle`/`Circle`
`[CONFIRMED]`. **Treat `TargetElementColor`/`RenderColorMode` as unverified; do not
build a mapping on them.** `[UNKNOWN]`

**F. Style-token roles** (custom props declared in `qml/style/*`, all `[CONFIRMED]`;
all values `[UNKNOWN]`) — 51 tokens:
`buttonColor`, `buttonPressedColor`, `buttonCheckedColor`, `buttonCheckedFocusColor`,
`buttonCheckedPressedColor`, `focusColor`, `focusLightColor`, `frameDarkColor`,
`frameLightColor`, `textColor`, `textDarkColor`, `textLightColor`, `textDisabledColor`,
`textDisabledLightColor`, `textLinkColor`, `textPlaceholderColor`, `textSelectionColor`,
`selectionColor`, `selectedTextColor`, `indicatorFrameColor`,
`indicatorFramePressedColor`, `indicatorFrameDisabledColor`, `indicatorPressedColor`,
`indicatorDisabledColor`, `scrollBarColor`, `scrollBarPressedColor`,
`tabButtonColor`, `tabButtonPressedColor`, `tabButtonCheckedPressedColor`,
`toolButtonColor`, `progressBarColor`, `pageIndicatorColor`, `separatorColor`,
`backgroundColor`, `overlayModalColor`, `overlayDimColor`, `linkColor`,
`disabledLightColor`, `disabledDarkColor`, `delegateColor`, `delegateFocusColor`,
`delegatePressedColor`, `focusPressedColor`, `darker`, `baselineOffset`,
`pageIndicatorColor`.
(These are **not** in stock QtQuick Controls 2 — verified by grepping
`/f/Scatt Basic/QtQuick/Controls.2/*.qml`, which only carries
`Default.overlayModalColor`/`Default.indicatorFrameColor`/`Default.focusColor`/
`Default.frameDarkColor`. So these 51 are SCATT's own additions = the SCATT theme
surface. `[CONFIRMED]`)

**G. Named QML colour literals in app code** `[CONFIRMED]`:
`lightcoral`, `skyblue` (RangeView_Timeline) · `blue`, `live`, `lightblue`
(Catalog SelectSessionStep / State_debug) · `white`, `lightgrey`, `black`, `grey`,
`transparent` (ShotList delegates) · `red` (SettingsEditor RadioButton) ·
`#bdbebf` (catalog checkbox).

**H. SVG fill colours** in `assets/` `[CONFIRMED]` — these tell us what *icons/graphics*
are drawn in, not what the chrome is: `#000000`/`black` (×77, monochrome Material glyphs),
`#fefefe`, `#f4f3f1`, `#8f8c89`, `#33383a` (4 assets — grey UI chrome graphics),
`#00E678` (green — `Filter Selected`), `#ff5722`/`#d94d22`/`#d84d22` (orange-red),
`#8bc34a`/`#77a646` (green), `#fffbdb` (pale yellow), `#010101`.

> **Observation:** `#00E678` (SCATT green) is one hue off STASYS `accent_good` `#00D26A`.
> `#ff5722` (SCATT orange-red) vs STASYS `accent_bad` `#FF5252` / `accent_ok` `#FFC107`.
> The two palettes are already near-neighbours in hue, which makes the mapping in §6.3
> cheap. `[CONFIRMED]` values, `[INFERENCE]` about intent.

### 6.3 The mapping table (the contract)

| SCATT role | Evidence | STASYS `COLORS` key | Notes |
|---|---|---|---|
| page / window background (`windowBackground`) | `[CONFIRMED]` name, value `[UNKNOWN]` | `bg_primary` `#0D0D0D` | |
| window text (`windowText`) | `[CONFIRMED]` name, value `[UNKNOWN]` | `text_primary` `#E8E8E8` | |
| panel / pane background (`Pane`, `Frame`, `Page` style) | `[CONFIRMED]` files, values `[UNKNOWN]` | `bg_secondary` `#1A1A1A` | SCATT `style/Pane.qml` + `style/Frame.qml` exist `[CONFIRMED]` |
| card / grouped-box background (`GroupBox`) | `[CONFIRMED]` file, value `[UNKNOWN]` | `bg_card` `#1E1E1E` | |
| elevated / popup / menu surface (`Popup`, `Menu`, `Dialog`, `Drawer`) | `[CONFIRMED]` files, values `[UNKNOWN]` | `bg_elevated` `#2A2A2A` | |
| input / table base (`TextField`, `TextArea`, `ComboBox` popup) | `[CONFIRMED]` files, values `[UNKNOWN]` | `bg_tertiary` `#252525` | |
| text primary (`textColor`, `textLightColor`) | `[CONFIRMED]` names | `text_primary` `#E8E8E8` | |
| text secondary (`textDarkColor`, `label` default) | `[CONFIRMED]` names | `text_secondary` `#A0A0A0` | |
| text muted / disabled (`textDisabledColor`, `textDisabledLightColor`) | `[CONFIRMED]` names | `text_muted` `#666666` | |
| placeholder (`textPlaceholderColor`) | `[CONFIRMED]` name | `text_muted` `#666666` | |
| border / frame (`frameDarkColor`, `separatorColor`) | `[CONFIRMED]` names | `border` `#333333` | SCATT splits light/dark frame (`frameLightColor`/`frameDarkColor`) `[CONFIRMED]`; STASYS has one `border` — map both here, or add `border_subtle` if a second tier is wanted `[INFERENCE]` |
| focus / selection ring (`focusColor`, `focusLightColor`) | `[CONFIRMED]` names | `border_active` `#00D26A` | STASYS's existing idiom (`core.py:3163`, `3515`) is green focus; keep |
| selection fill (`selectionColor`, `textSelectionColor`) | `[CONFIRMED]` names | `accent_blue` `#2196F3` at ~30 % alpha | text selection is not the same as "action" `[INFERENCE]` |
| selected text (`selectedTextColor`) | `[CONFIRMED]` name | `text_primary` `#E8E8E8` | |
| primary action (`buttonColor`, `toolButtonColor`) | `[CONFIRMED]` names | `accent_good` `#00D26A` | STASYS already styles primary buttons green (`core.py:3161` family) |
| pressed action (`buttonPressedColor`) | `[CONFIRMED]` name | `accent_good` + `dd` alpha (as `_stylized_button` does, `core.py:3150`) | |
| checked / active tab (`buttonCheckedColor`, `tabButtonCheckedPressedColor`) | `[CONFIRMED]` names | `accent_good` `#00D26A` | matches `QTabBar::tab:selected` (`core.py:3257`) |
| progress / busy (`progressBarColor`, `BusyIndicator`) | `[CONFIRMED]` file | `accent_blue` `#2196F3` | |
| positive / OK (`Filter Selected` `#00E678`) | `[CONFIRMED]` SVG value | `accent_good` `#00D26A` | near-identical hue |
| warning (`#fffbdb` pale-yellow, `#a28700`) | `[CONFIRMED]` SVG values | `accent_ok` `#FFC107` | |
| negative / error (`#ff5722`, `#d94d22`) | `[CONFIRMED]` SVG values | `accent_bad` `#FF5252` | |
| disabled control (`disabledLightColor`, `disabledDarkColor`, `indicatorDisabledColor`) | `[CONFIRMED]` names | `status_idle` `#555555` (bg) + `text_muted` `#666666` (fg) | |
| modal scrim (`overlayModalColor`, `overlayDimColor`) | `[CONFIRMED]` name | `bg_primary` `#0D0D0D` @ 60 % | STASYS has no scrim key; derive it `[INFERENCE]` |
| link (`linkColor`, `textLinkColor`) | `[CONFIRMED]` names | `accent_blue` `#2196F3` | About screen uses `<a href>` `[CONFIRMED]` |
| status: idle / arming / armed / cooldown | STASYS-only | `status_idle` / `status_arming` / `status_armed` / `status_cooldown` | **No SCATT equivalent** — these are STASYS's own shot-cycle states; keep as-is `[CONFIRMED]` (STASYS side) |
| score tiers elite…beginner | STASYS-only | `score_elite`…`score_beginner` | **No SCATT equivalent.** SCATT has numeric ring scores, not tiers. Keep as-is |

**Timeline literals** `lightcoral` / `skyblue` `[CONFIRMED]` in `RangeView_Timeline`:
their *role* is `[UNKNOWN]` (segment colours in a debug-adjacent region).
**Recommendation:** do **not** import them. Map timeline segments onto
`accent_blue` / `accent_ok` / `accent_bad` by segment meaning, or leave them `[UNKNOWN]`
until a real screenshot establishes intent. `[INFERENCE]`

### 6.4 Target rendering: keep ISSF colours or flip?

**STASYS today:** `AimCanvas`/`ShotTraceCanvas` render **SVG targets** via
`QSvgRenderer` at `core.py:2435` (render at `2452`), with a procedural ISSF fallback
`_draw_simple_rings` at `core.py:2456`. Target selection is
`cmb_target_type` (`core.py:3861`) with `10m Air Pistol (ISSF)` / `10m Air Rifle (ISSF)` /
`20m Air Pistol (ISSF)` / `50m Free Pistol (ISSF)`.

**SCATT's model** `[CONFIRMED]`: the target graphic is driven by **three user-settable
roles — `targetBackground`, `targetWhite`, `targetBlack`** — all three *persisted*
(`colors/…` in `QSettings`) and exposed as `ColorButton` rows in Settings with the exact
labels **`Target background` / `Target 'White'` / `Target 'Black'`**. That is
*semantic* separation: SCATT does not hardcode a light or dark target; it lets the user
choose. SCATT also has `printScoreRings` / `printScoreMarks` / `printScattLogo`
`[CONFIRMED]` as print-time toggles, i.e. rings and marks are independently switchable.

**Recommendation (for the implementer):**

1. **Keep STASYS's existing ISSF target colours as the default.** The SVG targets are
   real ISSF artwork and colour-correct; flipping them to match SCATT would make them
   *less* correct for shooting use, and SCATT does not mandate a polarity anyway
   (`targetWhite` and `targetBlack` are both user-settable). `[INFERENCE]` — high.
2. **Import SCATT's *structure*, not its values:** add the three-role split to
   `COLORS`-adjacent target settings so the target pane is independently themeable
   from the chrome. Suggested new keys (STASYS-side, names proposed, values = today's
   ISSF SVG behaviour):
   `target_background`, `target_light`, `target_dark`.
   `[INFERENCE]`
3. **On a dark chrome (`bg_primary #0D0D0D`), leave the target face alone.** A white
   ISSF target on a near-black page is the standard, legible arrangement and matches how
   shooters expect the target to look. Do **not** invert it to black-on-dark merely
   because the chrome is dark — that is precisely the failure the three-role split
   exists to avoid. `[INFERENCE]`
4. **Add a user override** (`ColorButton`, §5.1) if parity with SCATT's Settings
   "Colors" group is wanted. Low priority. `[INFERENCE]`

### 6.5 Summary palette rule

> **Every SCATT chrome colour is `[UNKNOWN]` in value.** This spec therefore maps
> *roles → STASYS keys* and forbids importing SCATT hex values, because there are none
> to import (0 UTF-16 hex literals in `scattbasic.exe`). The only SCATT colour values
> that *do* exist are 11 QML literals (§6.1/§6.2F) and SVG fills (§6.2H) — all of which
> are graphics/UI-accent colours, not surface colours.

---

## 7. Icon / asset inventory

206 carved SVGs in `scratch/scatt_extracted/assets/`. Resource **names** are in
`strings_utf16.txt` (the `images` block, lines ~10–195). Verdict key:
**RECOLOR-OK** = generic Material-style / generic geometry, safe to reuse *after*
recolouring to the STASYS palette and stripping any SCATT-specific meaning.
**RECREATE** = SCATT branding/wordmark/product art — **must not be copied**; design an
original STASYS equivalent for the same slot.

### 7.1 RECREATE — SCATT branding (do NOT copy)

| Asset name | Slot in UI | Evidence | Action |
|---|---|---|---|
| `scatt_logo_48px.svg` | **header logo**, first item of `MainWindow` `ToolBar` | `qrc:/images/scatt_logo_48px.svg` `[CONFIRMED]` | **RECREATE** — original STASYS wordmark/mark, same 48 px slot |
| `scattbasic.svg` | product icon / window icon | name `[CONFIRMED]` | **RECREATE** — STASYS app icon |
| `scatt_basic_icon_48px.svg`, `scatt_basic_icon_bw_48px.svg` | build-edition badge ("Basic") | names `[CONFIRMED]` | **RECREATE or OMIT** — STASYS has no Basic/Expert edition split |
| `scatt_expert_icon_48px.svg`, `scatt_expert_icon_bw_48px.svg` | build-edition badge ("Expert") | name `[CONFIRMED]` | **RECREATE or OMIT** — ditto. (`BasicBuild`/`ExpertBuild` strings `[CONFIRMED]` confirm the split exists) |
| `scatt_start_new_practice_96px.svg` | home card art — *Start new practice* | `newPracticeButton source0` `[CONFIRMED]` | **RECREATE** — original 96 px "new session" glyph |
| `scatt_start_new_practice_hc_96px.svg` | same, high-contrast variant | `[CONFIRMED]` | **RECREATE** |
| `scatt_open_file_96px.svg` | home card art — *Open recent sessions* | `catalogButton` `[CONFIRMED]` | **RECREATE** — original "open folder/session" glyph |
| `scatt_open_file_hc_96px.svg` | same, high-contrast variant | `[CONFIRMED]` | **RECREATE** |
| `scatt_device_connected_48.svg` | BatteryIndicator connection state | `[CONFIRMED]` (in `BatteryIndicator` pool, line 2339) | **RECREATE** — generic "sensor connected" glyph (no SCATT device silhouette) |
| `scatt_device_disconnected_48.svg` | BatteryIndicator connection state | `[CONFIRMED]` (line 2340) | **RECREATE** |
| `scatt_archery_icon_48px.svg` (`scattarchery_icon_48px.svg`) | discipline badge | name `[CONFIRMED]` | **RECREATE or OMIT** — STASYS is ISSF firearm/airgun only |
| `scatt_ic_person_48px.svg`, `scatt_ic_person_round_48px.svg`, `scatt_ic_person_square_48px.svg` | **P1 SelectShooter** shooter avatar (`source$`) | `qrc:/images/scatt_ic_person_48px.svg` in SelectShooterStep pool `[CONFIRMED]` | **RECREATE** — generic person glyph (Material `ic_person` is fine *as a substitute*, but do not copy SCATT's variant) |
| `scatt_do_correction_48px.svg` | *Make correction* action | name `[CONFIRMED]` | **RECREATE** — generic "re-aim / retarget" glyph |
| `scatt_optical_sensor_calibration_48px.svg` | **P4 Calibration** | name `[CONFIRMED]` | **RECREATE** — generic "calibrate" glyph |
| `scatt_shot_position_0…8_48px.svg` (9 files) | **ShotList direction column** — used as `qrc:/images/scatt_shot_position_` + index + `_48px.svg` | assembly confirmed in ShotList pool `[CONFIRMED]` | **RECREATE** — 9 generic direction arrows. *Note:* equivalents **already exist** in the carved assets as Sketch titles `Icons/Shotlist Table Icons/Direction/{Center,Up,Up Right,Right,Down Right,Down,Down Left,Left,Up Left}` `[CONFIRMED]` — **drawn from a non-SCATT source** (Sketch/Favorites set), so they are the natural starting point |
| `printout-logo.svg` | printed-target footer logo; gated by `printScattLogo` | `[CONFIRMED]` name + `printScattLogo` property | **RECREATE or OMIT** — STASYS has no printout feature today |
| `printout-mpi20/24/68.svg`, `printout-rifle-standing.svg` | printout target templates | names `[CONFIRMED]` | **OMIT** unless printable targets are added |

**Do not copy any `scatt_*` file.** The carved `assets/` are for *reading*, not shipping.

### 7.2 RECOLOR-OK — generic Material / generic geometry

All `ic_*.svg` are stock Material Design icons (the carved files confirm this: plain
`<svg … viewBox="0 0 48 48"><path d="…"/></svg>` with **no fill attribute**, i.e.
currentColor-tintable — e.g. `asset_000.svg`, `asset_001.svg`, `asset_002.svg`,
`asset_100.svg`, `asset_200.svg`). Safe to reuse after tinting to `COLORS`.

| Group | Names (from `strings_utf16.txt` `images` block) | Where used (evidence) |
|---|---|---|
| **Transport / replay** | `ic_play_arrow_48px`, `ic_play_circle_filled_48px`, `ic_play_circle_filled_white_48px`, `ic_play_circle_outline_48px`, `ic_pause_48px`, `ic_pause_circle_filled_48px`, `ic_pause_circle_outline_48px`, `ic_stop_48px`, `ic_replay_48px`, `ic_fast_forward_48px`, `ic_fast_rewind_48px`, `ic_skip_next_48px`, `ic_skip_previous_48px`, `ic_first_page_48px`, `ic_last_page_48px`, `ic_loop_48px`, `ic_repeat_48px`, `ic_slow_motion_video_48px` | replay transport `[CONFIRMED]`: `ic_play_arrow`/`ic_pause` in TargetView replay block, `ic_stop` on `stopReplayButton`, `ic_replay` on `deletedShotRowDelegate` restore button |
| **Device / connection** | `ic_usb_48px`, `ic_signal_wifi_4_bar_48px`, `ic_computer_48px`, `ic_laptop_48px`, `ic_laptop_mac_48px`, `ic_desktop_mac_48px` | **P2 ConfigureHardware** `[CONFIRMED]`: `ic_usb_48px` + `ic_signal_wifi_4_bar_48px` in its pool |
| **Battery** | `ic_battery_{20,30,50,60,80,90}_48px`, `ic_battery_full_48px`, `ic_battery_alert_48px`, `ic_battery_charging_{20,30,50,60,80,90,full}_48px` | `BatteryIndicator` / `RangeView_Title` `[CONFIRMED]` (ladder at lines 2325–2338) |
| **View / filter (ShotList modes)** | `View.svg`, `View Selected.svg`, `Filter.svg`, `Filter Selected.svg` | `[CONFIRMED]` in TargetView pool — the `displayMode` and sighting/deleted filter toggles. *These four are **not** Material; they carry Sketch titles `Icons/General/{View,View Selected,Filter,Filter Selected}` `[CONFIRMED]`.* Generic geometry + generic meaning → **RECOLOR-OK**, but recolour (they contain `#00E678`/`#33383a` `[CONFIRMED]`) rather than reuse raw |
| **Favorites** | `Favorites.svg`, `Favorites Selected.svg` | ShotList favorites column `[CONFIRMED]`; Sketch titles `Icons/General/Favorites{, Selected}` `[CONFIRMED]`. **RECOLOR-OK** |
| **Shot-table glyphs** | direction arrows (9×), `10`, `Z+`, `Z2`, `Z2+`, `10`-ring marks | ShotList columns `[CONFIRMED]`; Sketch titles `Icons/Shotlist Table Icons/...` `[CONFIRMED]`. **RECOLOR-OK** |
| **Window / layout** | `ic_fullscreen_48px`, `ic_fullscreen_exit_48px`, `ic_close_48px`, `ic_add_48px`, `ic_home_48px`, `ic_menu_48px`, `ic_more_vert_48px`, `ic_more_horiz_48px`, `ic_zoom_in_24px`, `ic_zoom_out_24px`, `ic_zoom_out_map_48px`, `ic_expand_more_48px`, `ic_expand_less_48px` | `[CONFIRMED]`: `ic_fullscreen`/`ic_fullscreen_exit` tooltips, `ic_close` on `closeButton`, `ic_add` on `newRangeButton`, `ic_home` on `homeButton`, `ic_menu` on `buttonMenu` |
| **Views / density** | `ic_view_module_48px`, `ic_view_module_black_48px`, `ic_view_list_48px`, `ic_view_list_black_48px`, `ic_view_headline_48px`, `ic_view_quilt_48px`, `ic_toc_48px`, `ic_apps_48px` | `[CONFIRMED]`: `ic_view_module_black_48px` = **Grid view**, `ic_view_list_black_48px` = **List view** (SelectTargetStep) |
| **Chevrons / nav** | `ic_chevron_left_48px`, `ic_chevron_right_48px`, `ic_arrow_back_48px`, `ic_arrow_forward_48px`, `ic_arrow_upward_48px`, `ic_arrow_downward_48px`, `ic_arrow_drop_{up,down}_48px`, `ic_keyboard_arrow_{left,right,up,down}` | navigation / combobox indicators `[CONFIRMED]` (`ic_arrow_drop_down` present in images block) |
| **Edit / file** | `ic_save_48px`, `ic_create_48px`, `ic_delete_48px`, `ic_delete_sweep_48px`, `ic_delete_forever_48px`, `ic_clear_48px`, `ic_clear_all_48px`, `ic_add_48px`, `ic_add_box_48px`, `ic_add_circle_48px`, `ic_add_circle_outline_48px`, `ic_remove_48px`, `ic_remove_circle_48px`, `ic_remove_circle_outline_48px`, `ic_undo_48px`, `ic_redo_48px`, `ic_folder_48px`, `ic_folder_open_48px`, `ic_create_new_folder_48px`, `ic_file_upload_48px`, `ic_file_download_48px`, `ic_attach_file_48px`, `ic_attachment_48px`, `ic_archive_48px`, `ic_search_48px`, `ic_find_in_page_48px`, `ic_print_48px`, `ic_pageview_48px` | `[CONFIRMED]`: `ic_print` + `ic_pageview` on Footer `print`/`printTargetPopup`; `ic_attach_file_48px` on SidePane `Comments`; catalog toolbar (Import/Export/Delete) `[INFERENCE]` |
| **Status / info** | `ic_info_48px`, `ic_info_outline_48px`, `ic_help_48px`, `ic_help_outline_24px`, `ic_warning_48px`, `ic_error_48px`, `ic_error_outline_48px`, `ic_report_problem_48px`, `ic_report_48px`, `ic_verified_user_48px`, `ic_block_48px`, `ic_cancel_48px`, `ic_lock_48px`, `ic_lock_open_48px`, `ic_lock_outline_48px` | `[CONFIRMED]`: **`ic_report_48px` = header `attentionButton`** (pulsing) → opens `Diagnostics` |
| **Time / history** | `ic_schedule_48px`, `ic_history_48px`, `ic_query_builder_48px`, `ic_timer` (`ic_query_builder`) | timeline / history `[INFERENCE]` |
| **Sorting / list** | `ic_sort_48px`, `ic_sort_by_alpha_24px`, `ic_filter_list_48px`, `ic_select_all_48px`, `ic_list_black_48px`, `ic_subject_48px` | catalog list controls `[INFERENCE]` |
| **Device settings** | `ic_settings_48px`, `ic_settings_applications_48px`, `ic_power_settings_new_48px`, `ic_sync_48px`, `ic_refresh_48px`, `ic_update_48px`, `ic_language_48px`, `ic_launch_48px`, `ic_exit_to_app_48px` | `[CONFIRMED]` `ic_language_48px` → `LanguageSelector`; Settings/device panels |
| **Discrete mode icons** | `ic_visibility_48px`/`ic_visibility_off_48px`, `ic_visibility_24px`, `ic_visibility_off_24px`, `ic_list_black_48px`, `ic_photo_camera_black_48px`, `ic_videocam_black_48px` | `[CONFIRMED]`: `ic_visibility`/`_off` = ShotList show/hide (`sizeHintShotRowHide`, `hideButton`, `displayPanel`); `ic_visibility_24px` = per-row hide hint; `ic_photo_camera_black_48px`/`ic_videocam_black_48px` = calibration preview (`componentPreviewShotImage`/`componentPreviewImage`) |
| **Misc** | `ic_volume_{up,down,off,mute}_48px`, `ic_hearing_48px`, `ic_chat_48px`, `ic_chat_bubble_48px`, `ic_chat_bubble_outline_48px`, `ic_touch_app_48px`, `ic_flag_48px`, `ic_text_format_48px`, `ic_create_48px`, `ic_lightbulb_outline_48px`, `ic_backspace_48px`, `ic_keyboard_*`, `ic_select_all_48px`, `ic_sync_48px`, `ic_folder_*`, `ic_share`-family, `ic_signal_*` | sound/announce settings (`shotSoundEnabled`, `pronounceScoreEnabled` `[CONFIRMED]`) `[INFERENCE]` |
| **printout geometry** | `printout-shot-position-0…8`, `printout-{speed,speed250ms,time,distance,calibre,result,index,offset,orientation,comments,z+,z2,z2+,hold10,hold10+,mpi20,mpi24,mpi68,rifle-standing,logo}.svg`, `printout-{index,offset,result,…}-column.svg` | printed report layout `[CONFIRMED]` names. Generic tabular geometry → **RECOLOR-OK** *if* a report feature is built; `printout-logo.svg` is the one exception (§7.1) |

### 7.3 Verdict roll-up

- **RECREATE (20 slots):** `scatt_logo_48px`, `scattbasic.svg`, `scatt_basic_icon*` (2),
  `scatt_expert_icon*` (2), `scatt_start_new_practice{,_hc}_96px` (2),
  `scatt_open_file{,_hc}_96px` (2), `scatt_device_{connected,disconnected}_48` (2),
  `scattarchery_icon_48px`, `scatt_ic_person{,_round,_square}_48px` (3),
  `scatt_do_correction_48px`, `scatt_optical_sensor_calibration_48px`,
  `scatt_shot_position_0…8_48px` (9), `printout-logo.svg`.
- **RECOLOR-OK:** every `ic_*`, the four `View/Filter` glyphs, `Favorites*`,
  the `Shotlist Table Icons` glyph set, and `printout-*` geometry (minus `printout-logo`).
- **RECOLOR-OK *with tinting required*:** `View.svg`, `View Selected.svg`, `Filter.svg`,
  `Filter Selected.svg`, `Favorites.svg`, `Favorites Selected.svg` — these ship with
  **literal fills** (`#00E678`, `#33383a`, `#fefefe` `[CONFIRMED]`) and will not match
  STASYS until recoloured.

---

## 8. Implementation notes for the PyQt5 build

### 8.1 Container mapping

| SCATT region | PyQt5 construct | Notes |
|---|---|---|
| `ApplicationWindow` + `header` ToolBar | keep `QMainWindow` + existing header `QFrame` (`core.py:3212`) | Add SCATT's header items: attention button (pulsing, → Diagnostics), fullscreen toggle. **Logo slot → STASYS mark** (§7.1) |
| `StackView stack` (modes) | **decision — see §8.4** | Do not build a QML-equivalent stack; Qt widgets already give you this |
| `RangeView` = R1…R5 | `QVBoxLayout(central)` containing: `R1` `QFrame`, `body` `QSplitter(Qt.Horizontal)`, `R4` `QFrame`, `R5` `QFrame` | `setHandleWidth(1)` to match SCATT's hairline look `[INFERENCE]` |
| `body` = R2 \| R3 | `QSplitter(Qt.Horizontal, handleWidth=1)` | Matches existing History split idiom (`core.py:3531`). SCATT's actual mechanism is `[UNKNOWN]` — `QSplitter` is a good stand-in, not a reconstruction |
| R3 side pane | `QScrollArea` (or the new `FocusScrollArea`, §5.1) | `enableSidePanel`/`displayPanel` → `QSplitter` collapse / `setVisible` |
| R4 timeline | `QFrame` + `ReplayBar` + timeline ruler | `displayTimeline` → `setVisible` |
| R5 footer | `QFrame` + `QHBoxLayout` | currently absent in STASYS — this is a **new structural element** |
| `RangeView_RegionError` | `QFrame` swapped into the `body` splitter's place | pattern reuse only (§3.5) |
| Wizard steps | `QStackedWidget` inside the screen body, or a `QDialog` wizard | see §8.5 |
| Popups (`ConfirmPopup`, `AddShooterPopup`, …) | `QDialog` subclasses | replace ad-hoc `QMessageBox` |
| Settings `ControlScrollView` + `GroupBox` | `QScrollArea` + `QGroupBox` + `QGridLayout` | matches `SettingsEditorMode` structure `[CONFIRMED]` |

### 8.2 Where existing STASYS canvases plug in

| SCATT element | STASYS widget | Line | Integration |
|---|---|---|---|
| R2 target rendering (`SolidBreach`, trace, aiming zone, zoom) | **`AimCanvas`** | `2092` | Occupies R2's target pane. Add: `homeButton` reset-zoom, `zoomIn/zoomOut/zoomToRing/zoomToFit`, `TargetScrollIndicator` overlay |
| R2 / trace colouring | **`ShotTraceCanvas`** | `2247` | Phase-coloured trace — this is the closest existing analogue to SCATT's `traceBeforeShot`/`traceAfterShot`/`trace` role split. Consider feeding it the §6.3 trace roles |
| R4 transport | **`ReplayBar`** | `2637` | Occupies R4's transport half; SCATT's segment timeline becomes a strip above/beside it |
| Shot list (compact) | **`ShotFilmStrip`** | `2901` | Stays as the compact horizontal strip (SCATT has no direct equivalent — SCATT's list is a *table*). Put it directly under R2 as a quick-nav strip |
| Shot list (full table) | **NEW `ShotTable(QTableView)`** | — | Implements §3.3: 15 togglable columns driven by `displayShotList*`-equivalent settings, `shotRow*Width` column widths, row-type delegates for `SerieTitleRow`/`ShotRow`/`SerieSummaryRow`/`SessionSummaryRow` |
| Shot cell | **`ShotChip`** | `2839` | Reuse as the delegate painter for the compact strip; the table uses its own delegate |
| R3 side pane content | **`SessionStatsWidget`** | `2984` | Promote into R3 as the summary block |
| R3 charts | **`SparklineWidget`** | `2777` | One `SparklineWidget` per chart; SCATT's four named charts (Distance / Coordination / Time shift / Speed) map to four instances. The `Ballistic ratio` / `filterCutoff` / `resampleRate` controls are **NEW** if parity is desired |
| R1 battery/connection | **NEW `BatteryIndicator`** | — | Only if battery-powered hardware lands; otherwise omit |
| Home launcher | **`ConnectionScreen`** | `1188` | Extend with the two 96 px launcher cards (`Start new practice` / `Open recent sessions`) |
| Buttons | **`_stylized_button`** | `3139` | Add an icon-only mode to serve `ImageToolButton` |
| Cards / grouped boxes | **`_card`** | `3156` | Maps to SCATT `GroupBox`; align padding with §8.3 |
| Stat tiles | **`_make_stat_card`** | `4157` | Maps to `SessionSummaryRow` / `summaryRowHeight` tiles |
| Diagnostics | **NEW popup** | — | Header `attentionButton` (`ic_report` + pulse) opens it |

### 8.3 Spacing / sizing — the `[UNKNOWN]` budget

**No SCATT pixel value is recoverable.** Every number below is therefore a *STASYS-side
proposal*, chosen to match what `core.py` already does — it is **not** a SCATT
measurement. Implementers must not cite these as "SCATT spacing".

| Quantity | SCATT | STASYS proposal (basis) |
|---|---|---|
| Page margins | `[UNKNOWN]` | `20,16` / `16,12` (already used: `core.py:3277`, `3501`) |
| Card padding | `[UNKNOWN]` | `16` (`_card`, `core.py:3164`) |
| Stack spacing | `[UNKNOWN]` | `12`–`14` (`core.py:3279`, `3503`) |
| Splitter handle | `[UNKNOWN]` | `1` px (`core.py:3532`) |
| Section label (eyebrow) | `[UNKNOWN]` | 10 px / 700 / `letter-spacing:1px` (`core.py:3328`) |
| R1 / R4 / R5 heights | `[UNKNOWN]` | pick from content; **do not invent a "SCATT height"** |
| R2 : R3 ratio | `[UNKNOWN]` | let `QSplitter` decide; persist the size like SCATT persists `window/*` |
| Shot-list row heights | `[UNKNOWN]` | derive from font height + `cellTopBottomPadding` equivalent |
| Label type scale | `[UNKNOWN]` | §5.4 |

SCATT *does* persist `window/x|y|width|height|visibility` `[CONFIRMED]` and
`appearance/targetGridCellWidth` `[CONFIRMED]` — so **persisting geometry is a SCATT
pattern worth copying**, even though the values are not.

### 8.4 The `QTabWidget` → mode-switch decision

SCATT has **modes** (`StackView` + `Ctrl+Tab` + a checkable header button group), not
tabs `[CONFIRMED]`. STASYS has `QTabWidget` with 5 tabs `[CONFIRMED]`.

Three options; **no evidence picks one** — this is a product decision, recorded as `[UNKNOWN]`:

| Option | What | Pros | Cons |
|---|---|---|---|
| **A — keep `QTabWidget` (recommended)** | Restyle per §5.1 `MyTabButton` mapping; apply §5.3 tab fate | Least code churn; keyboard already works; STASYS users know it | Diverges from SCATT's header-mode look |
| **B — header mode buttons** | Replace tab bar with a checkable `QButtonGroup` in the header, content in a `QStackedWidget`; bind `Ctrl+Tab`/`Ctrl+Shift+Tab` | Closest to SCATT `[CONFIRMED]` header pattern | Touches every tab builder (`core.py:3271, 3496, 3761, 3808`); higher regression risk |
| **C — hybrid** | Keep tabs for Shot Analysis / History / Settings; add SCATT's home launcher as a 0th "Home" mode reached before the wizard | Preserves both models; mirrors SCATT's `UndefinedMode` home | Two navigation idioms at once |

**Recommendation: A for this pass, C as the target state.** Rationale: the deliverable is
a *layout reskin*, and the header contains SCATT-specific items (attention pulse,
fullscreen, logo) that STASYS wants anyway — those can be added to the existing header
without converting navigation. Revisit when the wizard (§8.5) lands.
`[INFERENCE]`

### 8.5 Wizard implementation

SCATT's wizard is `practiceStep`-driven with `RangeView_<Mode>_<Step>.qml` files loaded by
`setSource` on change `[CONFIRMED]`. STASYS equivalent:

- `QStackedWidget` inside the screen body, one page per step
  (`SelectShooter`, `ConfigureHardware`, `SelectTarget`, `Calibration`, `Shooting`),
  with the R1 title string switching on the step (SCATT's format strings
  `Select shooter` / `Configure hardware | %1` / `Select target | %1` /
  `Calibration | %1 | %2 | %3%4` / `Practice | %1 | %2 | %3 | %4%5` are `[CONFIRMED]`
  and are a good template for STASYS's own title bar).
- Back/Next wired exactly to the confirmed edges (§2.2). **Honor the evidence order**
  (ConfigureHardware before SelectTarget) unless the product owner overrides it.
- `ShootingStep` is not a form — it is the full R1–R5 screen. So the wizard pages
  occupy R2's slot while `ShootingStep` restores the full body.
  `[INFERENCE]`
- Steps that need the target/chart machinery (`SelectTarget`, `Calibration`) reuse
  `AimCanvas`; `Calibration`'s preview overlays correspond to
  `ShootingView_Maximized`'s `componentPreviewImage` / `componentCalibrationTarget`
  `[CONFIRMED]` — port as overlay widgets on `AimCanvas`.

### 8.6 Settings editor

Rebuild `core.py:3808` as `QScrollArea` → `QGroupBox` per §4.2 group → `QGridLayout`
(matches `ControlScrollView` + `GroupBox` + `GridLayout columns` `[CONFIRMED]`).
Add the **Colors** group last with `ColorButton` widgets bound to §6.3 keys.
Add `ButtonWithConfirmPopup` equivalents for `Ask for confirmation when closing the
program` and `Reset storage`.
`[INFERENCE]` on ordering (SCATT's group *order* is `[UNKNOWN]`; the strings' order above
is the pool order, not necessarily layout order).

### 8.7 What NOT to build

- **Region lock / `RangeView_RegionError` content** — STASYS has no market restriction.
- **`RangeView_State_debug` / `RangeView_Emulator_debug`** — developer-only.
- **`MacOSMenuBar`** — Windows target.
- **Printout / `PrintTargetPopup` / `printout-*.svg`** — no print feature in STASYS.
- **Wi-Fi / `ic_signal_wifi` device profiles, firmware update flows** — SCATT hardware.
- **Any `scatt_*` asset** (§7.1) — trademarked/branded.
- **SCATT's colour *values*** — none are recoverable (§6.5).

---

## Appendix A — Evidence index

| Claim class | Where it comes from | Confidence |
|---|---|---|
| A file exists | `resource_paths.txt` (114 paths) | `[CONFIRMED]` |
| A property / signal / ID / literal string exists | `strings_utf16.txt`, `strings_ui.txt` | `[CONFIRMED]` |
| Which file a symbol belongs to | §1.2 terminator-path method | `[INFERENCE]` |
| Widget role / layout relationship | naming + Qt idiom + cross-set agreement (§3.3) | `[INFERENCE]` |
| Step order | enum order + `goto…Step` edges (§2.2) | `[INFERENCE]` |
| An icon's slot in the UI | adjacent `qrc:/images/…` path + object ID in the same pool | `[CONFIRMED]` for path, `[INFERENCE]` for slot |
| SCATT chrome hex values | — | **`[UNKNOWN]`** (0 UTF-16 hex literals in exe) |
| Any pixel spacing / proportion / font size of SCATT | — | **`[UNKNOWN]`** |
| `TargetElementColor`, `RenderColorMode` | not found in evidence or exe | **`[UNKNOWN]`** — unverified, do not build on |
| QML source text | does not exist | **n/a — never quoted in this document** |
