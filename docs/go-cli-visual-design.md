# Sigma-Quant Stream -- Visual Design System

**Version:** 1.0.0
**Last Updated:** 2026-02-09
**Author:** UX Director Agent
**Stack:** Go + Bubble Tea + Lipgloss
**Aesthetic:** Sharian (Dark / Gotham / Cyberpunk / Tech-Forward)

---

## Table of Contents

1. [Design Philosophy](#1-design-philosophy)
2. [Color Palettes (3 Options)](#2-color-palettes)
3. [Typography & Text Styling](#3-typography--text-styling)
4. [ASCII Art & Banners](#4-ascii-art--banners)
5. [Animation Specifications](#5-animation-specifications)
6. [Component Visual Specs](#6-component-visual-specs)
7. [Responsive Design](#7-responsive-design)
8. [Accessibility Considerations](#8-accessibility-considerations)
9. [Lipgloss Implementation Guide](#9-lipgloss-implementation-guide)
10. [Dual Experience Mode](#10-dual-experience-mode)

---

## 1. Design Philosophy

### Core Tenets

This is not a terminal utility. This is a **command bridge**. Every pixel of character
space conveys intent. The user is a quant operator commanding an autonomous strategy
research factory. The interface should feel like stepping into a fighter cockpit or
the Batcave's main terminal -- dark, precise, powerful, and alive.

**Density with clarity.** Show maximum information without overwhelming. Every data
point earns its screen real estate.

**Motion with purpose.** Animations are not decoration. They communicate state
transitions, draw attention to changes, and create the sensation of a living system.

**Restraint in color.** A dark interface gains power from what it does NOT illuminate.
Color is a signal. Use it surgically.

### Mood Board (Conceptual References)

```
+------------------------------------------------------------------+
|  Batman's Batcomputer    |  Bloomberg Terminal    |  Cyberpunk UI |
|  Dark, mission-critical  |  Dense, professional   |  Neon accents |
|  Blue-lit cave walls     |  Monochrome + orange   |  Animated HUD |
+------------------------------------------------------------------+
|  SpaceX Launch Console   |  Tron Legacy UI        |  LCARS (Trek) |
|  Clean telemetry         |  Geometric glow        |  Panel-based  |
|  Progress indicators     |  Cyan on black         |  Status bars  |
+------------------------------------------------------------------+
```

---

## 2. Color Palettes

### PALETTE 1: "Gotham Night"

*Batman's cave meets Bloomberg terminal. Restrained, professional, powerful.*
*Think: blue-lit concrete walls, glowing monitors in darkness, rain on glass.*

```
BACKGROUNDS
  bg-primary    #0B0E14   Deep void black (main background)
  bg-secondary  #121821   Charcoal navy (panels, cards)
  bg-surface    #1A2130   Slate blue-gray (elevated surfaces)
  bg-hover      #222D3F   Steel blue (hover/focus highlight)

TEXT
  text-primary    #C8CED8   Cool silver (body text)
  text-secondary  #7E8A9A   Muted steel (secondary labels)
  text-muted      #4A5568   Dark gray (disabled, timestamps)
  text-accent     #4FC1E9   Ice cyan (links, interactive elements)

ACCENTS
  accent-primary  #4FC1E9   Ice cyan (primary actions, focus rings)
  accent-success  #2ECC71   Signal green (pass, active, healthy)
  accent-warning  #F39C12   Amber alert (caution, degraded)
  accent-error    #E74C3C   Crimson red (fail, critical, rejected)
  accent-info     #3498DB   Steel blue (informational)
  accent-highlight #6C5CE7  Soft violet (promotions, special events)

BORDERS & SEPARATORS
  border-primary  #2A3444   Subtle blue-gray (panel borders)
  border-active   #4FC1E9   Ice cyan (active panel border)
  border-muted    #1E2836   Near-invisible (subtle dividers)

GRADIENTS (for emphasis bars, headers)
  gradient-start  #0B0E14
  gradient-end    #1A2130
```

#### Gotham Night -- Dashboard Mockup

```
    Colors: bg=#0B0E14 | panels=#121821 | borders=#2A3444 | cyan=#4FC1E9
            green=#2ECC71 | amber=#F39C12 | text=#C8CED8 | muted=#7E8A9A

    +=========================================================================+
    |                                                                [cyan]   |
    |   S I G M A - Q U A N T   S T R E A M         v0.1.0   [12:34:05 UTC]  |
    |   ─────────────────────────────────────────────────────────────────────  |
    |                                                                         |
    |   [PANEL: bg-secondary #121821, border: #2A3444, rounded corners]       |
    |   ┌─ WORKERS ──────────────────────┐  ┌─ QUEUE DEPTH ────────────────┐  |
    |   │                                │  │                              │  |
    |   │  [cyan dot] RESEARCHER  ACTIVE │  │  hypotheses    ██████░░  12  │  |
    |   │  [green dot] BACKTESTER ACTIVE │  │  backtest_q    ████░░░░   8  │  |
    |   │  [green dot] EVALUATOR  IDLE   │  │  eval_q        ██░░░░░░   4  │  |
    |   │  [amber dot] PROMOTER   WAIT   │  │  promotion_q   ░░░░░░░░   0  │  |
    |   │                                │  │                              │  |
    |   └────────────────────────────────┘  └──────────────────────────────┘  |
    |                                                                         |
    |   ┌─ STRATEGY PIPELINE ────────────────────────────────────────────┐    |
    |   │                                                                │    |
    |   │  [green]  STR-042  YM_ORB_Breakout     sharpe: 2.14   GOOD    │    |
    |   │  [amber]  STR-041  ES_MeanRev_v3       sharpe: 1.67   REVIEW  │    |
    |   │  [red]    STR-040  NQ_Momentum_fail    sharpe: 0.42   REJECT  │    |
    |   │  [cyan]   STR-039  GC_Counter_v2       sharpe: 1.89   TESTING │    |
    |   │  [silver] STR-038  ES_VWAP_Bounce      sharpe: ---    QUEUED  │    |
    |   │                                                                │    |
    |   └────────────────────────────────────────────────────────────────┘    |
    |                                                                         |
    |   ┌─ THROUGHPUT ───────────────────────────────────────────────────┐    |
    |   │  [cyan sparkline]  Strategies/hr:  4.2   ▂▃▅▇█▇▅▃▂▃▅▇        │    |
    |   │  [green sparkline] Backtests/hr:  12.8   ▃▅▇█▇▅▃▂▃▅▇█        │    |
    |   └────────────────────────────────────────────────────────────────┘    |
    |                                                                         |
    |   [muted]  Press ? for help  |  q to quit  |  Tab to switch panels     |
    +=========================================================================+
```

---

### PALETTE 2: "Neon Ops"

*Cyberpunk 2077 meets hacker aesthetic. Vibrant, high-energy, futuristic.*
*Think: rain-slick streets reflecting neon, holographic HUDs, electric current.*

```
BACKGROUNDS
  bg-primary    #0D0221   Midnight purple-black (main background)
  bg-secondary  #150734   Deep indigo (panels, cards)
  bg-surface    #1B0A45   Royal purple-dark (elevated surfaces)
  bg-hover      #251258   Electric purple-dark (hover/focus)

TEXT
  text-primary    #E0D7F5   Lavender white (body text)
  text-secondary  #9B8FC2   Dusty violet (secondary labels)
  text-muted      #5C4F82   Faded purple (disabled, timestamps)
  text-accent     #00FFFF   Electric cyan (links, interactive)

ACCENTS
  accent-primary  #00FFFF   Electric cyan (primary actions)
  accent-secondary #FF00FF  Hot magenta (secondary accent)
  accent-success  #39FF14   Matrix green (pass, active)
  accent-warning  #FFD700   Neon gold (caution, degraded)
  accent-error    #FF3366   Hot pink-red (fail, critical)
  accent-info     #7B68EE   Medium slate blue (informational)
  accent-highlight #FF00FF  Hot magenta (promotions, celebrations)

BORDERS & SEPARATORS
  border-primary  #2D1B69   Purple border (panel borders)
  border-active   #00FFFF   Electric cyan (active panel border)
  border-glow     #FF00FF   Magenta glow (special emphasis)
  border-muted    #1A0D3D   Near-invisible purple (subtle dividers)

GRADIENTS
  gradient-cyber-start  #0D0221
  gradient-cyber-mid    #150734
  gradient-cyber-end    #00FFFF  (used sparingly for glow effects)
```

#### Neon Ops -- Dashboard Mockup

```
    Colors: bg=#0D0221 | panels=#150734 | borders=#2D1B69 | cyan=#00FFFF
            magenta=#FF00FF | green=#39FF14 | gold=#FFD700 | text=#E0D7F5

    +=========================================================================+
    |                                                            [cyan glow]  |
    |   ///  S I G M A - Q U A N T  ///          v0.1.0   [12:34:05 UTC]      |
    |   [magenta line]  ================================================      |
    |   [cyan subtitle] AUTONOMOUS STRATEGY RESEARCH FACTORY                  |
    |                                                                         |
    |   [PANEL: bg=#150734, border glow: cyan, double-line border]            |
    |   +== WORKERS =====================+  +== QUEUE STATUS ==============+  |
    |   ||                               |  ||                             |  |
    |   ||  [cyan pulse]  RESEARCHER  ON |  ||  hypotheses  [cyan]  >>  12 |  |
    |   ||  [green pulse] BACKTESTER  ON |  ||  backtest_q  [green] >>   8 |  |
    |   ||  [green]       EVALUATOR  IDL |  ||  eval_q      [gold]  >>   4 |  |
    |   ||  [gold blink]  PROMOTER   SLP |  ||  promotion_q [muted] >>   0 |  |
    |   ||                               |  ||                             |  |
    |   +================================+  +==============================+  |
    |                                                                         |
    |   +== STRATEGY FEED ================================================+  |
    |   ||                                                                 |  |
    |   ||  [green glow]  #042  YM_ORB_Breakout    S:2.14  >> GOOD        |  |
    |   ||  [gold]        #041  ES_MeanRev_v3      S:1.67  >> REVIEW      |  |
    |   ||  [pink-red]    #040  NQ_Momentum_fail   S:0.42  >> REJECT      |  |
    |   ||  [cyan flash]  #039  GC_Counter_v2      S:1.89  >> TESTING     |  |
    |   ||  [muted]       #038  ES_VWAP_Bounce     S:---   >> QUEUED      |  |
    |   ||                                                                 |  |
    |   +==================================================================+  |
    |                                                                         |
    |   +== LIVE METRICS =================================================+  |
    |   ||  [cyan]    Strat/hr: 4.2  [magenta sparkline] ▂▃▅▇█▇▅▃▂▃▅▇   |  |
    |   ||  [green]   BT/hr:  12.8   [green sparkline]   ▃▅▇█▇▅▃▂▃▅▇█   |  |
    |   +==================================================================+  |
    |                                                                         |
    |   [magenta] >_ [cyan] Type command or press ? for help                  |
    +=========================================================================+
```

---

### PALETTE 3: "Dark Knight"

*Pure blacks with gold/amber accents. Luxury meets tech.*
*Think: Lamborghini dashboard in the dark. Rolex on a matte black wrist.*

```
BACKGROUNDS
  bg-primary    #000000   True black (main background)
  bg-secondary  #0A0A0A   Near-black (panels, cards)
  bg-surface    #141414   Charcoal (elevated surfaces)
  bg-hover      #1E1E1E   Dark gray (hover/focus highlight)

TEXT
  text-primary    #D4AF37   Antique gold (headings, emphasis)
  text-secondary  #B8B8B8   Silver (body text)
  text-muted      #555555   Medium gray (disabled, timestamps)
  text-accent     #FFD700   Bright gold (links, interactive)

ACCENTS
  accent-primary  #D4AF37   Antique gold (primary actions, focus)
  accent-secondary #FFD700  Bright gold (hover states)
  accent-success  #50C878   Emerald green (pass, active)
  accent-warning  #FF8C00   Dark orange (caution, degraded)
  accent-error    #DC143C   Crimson (fail, critical, rejected)
  accent-info     #708090   Slate gray (informational)
  accent-highlight #D4AF37  Gold (promotions, celebrations)

BORDERS & SEPARATORS
  border-primary  #1E1E1E   Subtle charcoal (panel borders)
  border-active   #D4AF37   Antique gold (active panel border)
  border-muted    #0F0F0F   Near-invisible (subtle dividers)
  border-luxury   #FFD700   Bright gold (special emphasis)

GRADIENTS
  gradient-knight-start  #000000
  gradient-knight-end    #141414
  gradient-gold-start    #D4AF37
  gradient-gold-end      #FFD700
```

#### Dark Knight -- Dashboard Mockup

```
    Colors: bg=#000000 | panels=#0A0A0A | borders=#1E1E1E | gold=#D4AF37
            bright-gold=#FFD700 | emerald=#50C878 | orange=#FF8C00
            silver=#B8B8B8 | crimson=#DC143C

    +=========================================================================+
    |                                                                         |
    |           [gold on black, elegant spacing]                              |
    |                                                                         |
    |           S I G M A  -  Q U A N T                                       |
    |           ___________________________                                   |
    |                                                                         |
    |           [silver, small] Strategy Research Factory  v0.1.0             |
    |                                                                         |
    |   [gold thin line] ─────────────────────────────────────────────────    |
    |                                                                         |
    |   [PANEL: bg=#0A0A0A, border: thin gold #D4AF37]                       |
    |   ┌─────────────────────────────────┐  ┌────────────────────────────┐   |
    |   │  [gold] W O R K E R S           │  │  [gold] Q U E U E S       │   |
    |   │                                 │  │                            │   |
    |   │  [emerald] RESEARCHER   ACTIVE  │  │  hypotheses    12  [gold] │   |
    |   │  [emerald] BACKTESTER   ACTIVE  │  │  backtest_q     8  [gold] │   |
    |   │  [silver]  EVALUATOR    IDLE    │  │  eval_q          4  [sil] │   |
    |   │  [orange]  PROMOTER     WAIT    │  │  promotion_q     0  [mut] │   |
    |   │                                 │  │                            │   |
    |   └─────────────────────────────────┘  └────────────────────────────┘   |
    |                                                                         |
    |   ┌─ [gold] S T R A T E G I E S ───────────────────────────────────┐   |
    |   │                                                                 │   |
    |   │  [emerald]  042  YM_ORB_Breakout     2.14   GOOD               │   |
    |   │  [orange]   041  ES_MeanRev_v3       1.67   REVIEW             │   |
    |   │  [crimson]  040  NQ_Momentum_fail    0.42   REJECTED           │   |
    |   │  [gold]     039  GC_Counter_v2       1.89   TESTING            │   |
    |   │  [muted]    038  ES_VWAP_Bounce      ---    QUEUED             │   |
    |   │                                                                 │   |
    |   └─────────────────────────────────────────────────────────────────┘   |
    |                                                                         |
    |   ┌─ [gold] T H R O U G H P U T ──────────────────────────────────┐   |
    |   │  Strategies/hr   4.2   [gold sparkline] ▂▃▅▇█▇▅▃▂▃▅▇          │   |
    |   │  Backtests/hr   12.8   [emerald spark]  ▃▅▇█▇▅▃▂▃▅▇█          │   |
    |   └─────────────────────────────────────────────────────────────────┘   |
    |                                                                         |
    |   [muted] ? help   q quit   tab navigate              [gold] 12:34 UTC |
    +=========================================================================+
```

---

### Palette Comparison Matrix

```
+------------------+-------------------+-------------------+-------------------+
|   Attribute      |   Gotham Night    |    Neon Ops       |   Dark Knight     |
+------------------+-------------------+-------------------+-------------------+
|   Vibe           |   Professional    |   Cyberpunk       |   Luxury          |
|   Energy         |   Calm, focused   |   Electric, bold  |   Commanding      |
|   Primary BG     |   #0B0E14 navy    |   #0D0221 purple  |   #000000 black   |
|   Key Accent     |   #4FC1E9 cyan    |   #00FFFF e-cyan  |   #D4AF37 gold    |
|   Text Feel      |   Cool silver     |   Lavender white  |   Silver + gold   |
|   Border Style   |   Rounded, subtle |   Double, glowing |   Thin, precise   |
|   Best For       |   Long sessions   |   Demos, wow      |   Premium brand   |
|   Eye Fatigue    |   Low             |   Medium          |   Low             |
|   Readability    |   Excellent       |   Good            |   Excellent       |
+------------------+-------------------+-------------------+-------------------+
```

---

## 3. Typography & Text Styling

### Font Recommendations

| Priority | Font | Why | Ligatures |
|----------|------|-----|-----------|
| **1st** | JetBrains Mono | Best readability at small sizes, excellent box-drawing | Yes |
| **2nd** | Cascadia Code | Ships with Windows Terminal, clean | Yes |
| **3rd** | Fira Code | Wide language support, battle-tested | Yes |
| **Fallback** | SF Mono / Menlo | macOS defaults, always available | No |

### Nerd Font Requirement

Install the Nerd Font variant (e.g., `JetBrainsMono Nerd Font`) for icon support.

### Icon Reference (Nerd Font)

```
Workers & Status:
    Active worker       (or green filled circle)
    Idle worker         (or dimmed circle)
    Sleeping worker     (zzz or moon icon)
    Error state

Queue & Flow:
  >>  Flow direction      (or arrow icons)
    Strategy/research
    Backtest
    Evaluation

Status:
    Pass / Success
    Fail / Error
    Warning
    Info

Navigation:
    Expand/collapse    /
  >>  Breadcrumb separator
    Search
    Settings
```

### Text Hierarchy

```
LEVEL       STYLE                     USAGE                           EXAMPLE
------      -----                     -----                           -------
H1          UPPERCASE, bold,          Screen titles, major sections   "S T R A T E G I E S"
            letter-spaced,
            accent color

H2          Title Case, bold,         Panel headers, tab labels       "Worker Status"
            primary text color

H3          Title Case, normal,       Sub-sections within panels      "Session Details"
            secondary text color

Body        Normal weight,            Data values, descriptions       "sharpe: 2.14"
            primary text color

Label       Normal weight,            Field labels, column headers    "Tasks completed:"
            secondary text color

Muted       Normal weight,            Timestamps, disabled text,      "45m ago"
            muted text color          help hints

Accent      Normal or bold,           Interactive elements, links,    "[Enter] to select"
            accent color              key bindings

Mono-num    Tabular/fixed-width       Numbers, metrics, IDs           "STR-042"
            primary text color
```

### Letter Spacing for Headers

H1 headers use spaced characters for the Gotham aesthetic:

```
Standard:   "STRATEGIES"
Spaced:     "S T R A T E G I E S"
Wide:       "S  T  R  A  T  E  G  I  E  S"
```

Implementation helper:

```go
func SpaceLetters(s string) string {
    runes := []rune(strings.ToUpper(s))
    return strings.Join(strings.Split(string(runes), ""), " ")
}
```

### Bold/Italic/Underline Rules

| Style | When to Use | When NOT to Use |
|-------|-------------|-----------------|
| **Bold** | Active values, status labels, user actions | Body text, descriptions |
| *Italic* | Not recommended in TUI (poor rendering in most terminals) | Anywhere |
| Underline | Active tab indicator, focused link | Headers, body text |

---

## 4. ASCII Art & Banners

### Main Logo -- Standard (80 cols)

```
 ____  _                         ___                   _
/ ___|(_) __ _ _ __ ___   __ _  / _ \ _   _  __ _ _ __ | |_
\___ \| |/ _` | '_ ` _ \ / _` || | | | | | |/ _` | '_ \| __|
 ___) | | (_| | | | | | | (_| || |_| | |_| | (_| | | | | |_
|____/|_|\__, |_| |_| |_|\__,_| \__\_\\__,_|\__,_|_| |_|\__|
         |___/
```

### Main Logo -- Wide (120+ cols)

```
 ███████╗██╗ ██████╗ ███╗   ███╗ █████╗        ██████╗ ██╗   ██╗ █████╗ ███╗   ██╗████████╗
 ██╔════╝██║██╔════╝ ████╗ ████║██╔══██╗      ██╔═══██╗██║   ██║██╔══██╗████╗  ██║╚══██╔══╝
 ███████╗██║██║  ███╗██╔████╔██║███████║█████╗██║   ██║██║   ██║███████║██╔██╗ ██║   ██║
 ╚════██║██║██║   ██║██║╚██╔╝██║██╔══██║╚════╝██║▄▄ ██║██║   ██║██╔══██║██║╚██╗██║   ██║
 ███████║██║╚██████╔╝██║ ╚═╝ ██║██║  ██║      ╚██████╔╝╚██████╔╝██║  ██║██║ ╚████║   ██║
 ╚══════╝╚═╝ ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝       ╚══▀▀═╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝
```

### Main Logo -- Compact (fits anywhere)

```
[SQ] SIGMA-QUANT
```

### Main Logo -- Mini Icon

```
SQ
```

### Tagline Options

```
Primary:    "Autonomous Strategy Research Factory"
Short:      "Strategy Factory"
Technical:  "Hypothesize. Backtest. Evaluate. Deploy."
Dramatic:   "The Machine Never Sleeps."
```

### Boot Screen Art

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│    ____  _                         ___                   _       │
│   / ___|(_) __ _ _ __ ___   __ _  / _ \ _   _  __ _ _ __ | |_   │
│   \___ \| |/ _` | '_ ` _ \ / _` || | | | | | |/ _` | '_ \| __|  │
│    ___) | | (_| | | | | | | (_| || |_| | |_| | (_| | | | | |_   │
│   |____/|_|\__, |_| |_| |_|\__,_| \__\_\\__,_|\__,_|_| |_|\__|  │
│            |___/                                                 │
│                                                                  │
│            Autonomous Strategy Research Factory                   │
│            ──────────────────────────────────                    │
│            v0.1.0                                                │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 5. Animation Specifications

### 5.1 Startup Boot Sequence

**Total target duration: 2.5 seconds**

The boot sequence is the first impression. It should feel like powering on a sophisticated
machine -- not instantaneous (too cheap), not slow (frustrating), but a deliberate ignition.

#### Phase 1: Logo Reveal (0ms - 600ms)

```
Frame 0 (0ms):     [empty screen, bg-primary only]

Frame 1 (50ms):    [single cursor blink at center]
                    _

Frame 2 (100ms):   [line draws outward from center]
                    ──────

Frame 3 (200ms):   [box frame starts forming -- top-left corner first]
                    ┌──────
                    │

Frame 4 (300ms):   [box completes]
                    ┌──────────────────────────────────────┐
                    │                                      │
                    │                                      │
                    │                                      │
                    └──────────────────────────────────────┘

Frame 5 (400ms):   [logo characters typewrite in, left to right]
                    ┌──────────────────────────────────────┐
                    │  S I G M A - Q U A N T               │
                    │                                      │
                    │                                      │
                    └──────────────────────────────────────┘

Frame 6 (500ms):   [tagline fades in (muted -> secondary -> primary)]
                    ┌──────────────────────────────────────┐
                    │  S I G M A - Q U A N T               │
                    │  Autonomous Strategy Research Factory │
                    │                                      │
                    └──────────────────────────────────────┘

Frame 7 (600ms):   [version + border accent color activates]
                    ┌──────────────────────────────────────┐  <- border now accent color
                    │  S I G M A - Q U A N T               │
                    │  Autonomous Strategy Research Factory │
                    │  v0.1.0                               │
                    └──────────────────────────────────────┘
```

#### Phase 2: Subsystem Init (600ms - 2000ms)

Each subsystem checks in sequentially, typewriter-style:

```
Timing     Display                                              State
------     -------                                              -----
 600ms     Initializing systems...                              [muted, typewriter]

 700ms     [spinner] Loading configuration...                   [accent]
 850ms      Configuration loaded                               [success]

 900ms     [spinner] Connecting to queues...                    [accent]
1100ms      Queue broker online                                [success]

1150ms     [spinner] Initializing workers...                    [accent]
1400ms      4 workers registered                               [success]

1450ms     [spinner] Loading strategy pipeline...               [accent]
1700ms      Pipeline ready (42 strategies tracked)             [success]

1750ms     [spinner] Running health check...                    [accent]
2000ms      All systems nominal                                [success, bold]
```

Visual rendering of the above:

```
┌──────────────────────────────────────────────────────────────┐
│  S I G M A - Q U A N T    v0.1.0                             │
│  Autonomous Strategy Research Factory                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│   Configuration loaded                                      │
│   Queue broker online                                       │
│   4 workers registered                                      │
│   Pipeline ready (42 strategies tracked)                    │
│  [spinner] Running health check...                           │
│                                                              │
│  ████████████████████████████████████░░░░░  85%              │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

#### Phase 3: Dashboard Materialize (2000ms - 2500ms)

```
2000ms     Boot banner dissolves (lines fade top-to-bottom)
2100ms     Dashboard panels draw in from edges:
             - Top bar slides down from top
             - Left panels slide in from left
             - Right panels slide in from right
             - Bottom bar slides up from bottom
2300ms     Data populates (numbers tick up from 0 to actual values)
2500ms     Dashboard fully interactive, cursor positioned
```

#### Spinner Styles

```
Braille dots (smooth):   ⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏
Block sweep:             ▏ ▎ ▍ ▌ ▋ ▊ ▉ █
Pulse dot:               ○ ◔ ◑ ◕ ● ◕ ◑ ◔
Line:                    ─ \ │ / ─ \ │ /
Gotham (recommended):    ◇ ◈ ◆ ◈   (diamond pulse)
```

### 5.2 Dashboard Animations

#### Real-Time Number Ticking

When a value changes, it counts up/down to the new value over 300ms:

```
Before:   Strategies: 41
Tick 1:   Strategies: 41  (50ms, stays)
Tick 2:   Strategies: 42  (flash accent color for 200ms)
Tick 3:   Strategies: 42  (return to normal color)
```

Implementation: linear interpolation over N frames, then color flash.

#### Sparkline Animation

New data points enter from the right, existing points scroll left:

```
Frame 0:  ▂▃▅▇█▇▅▃▂▃▅▇
Frame 1:   ▃▅▇█▇▅▃▂▃▅▇█    <- new point (█) enters right
Frame 2:    ▅▇█▇▅▃▂▃▅▇█▅   <- scroll continues
```

Update interval: every 5 seconds for throughput metrics.

Sparkline character set:

```
Blocks:  ▁ ▂ ▃ ▄ ▅ ▆ ▇ █   (8 levels)
```

#### Worker Status Pulse

Active workers have a pulsing indicator to show liveness:

```
Cycle (800ms total):
  0ms    [bright accent]
200ms    [dim accent]
400ms    [bright accent]
600ms    [dim accent]
800ms    [restart]
```

Idle workers show a solid dim dot. Sleeping workers show a slow fade cycle (2s).

#### Strategy Promotion Celebration

When a strategy reaches "good" or "prop_firm_ready":

```
Frame 0:     STR-042  YM_ORB_Breakout     EVALUATING
Frame 1:     ============ PROMOTED ============       <- flash line, accent highlight
Frame 2:     STR-042  YM_ORB_Breakout     GOOD       <- gold/green text
Frame 3:     STR-042  YM_ORB_Breakout     GOOD       <- subtle glow pulse 3x
Frame 4:     (normal display resumes)
```

For `prop_firm_ready` (the highest tier), add a brief box highlight:

```
   ╔══════════════════════════════════════════════════╗
   ║  PROP FIRM READY   STR-042  YM_ORB_Breakout     ║
   ║  Sharpe: 2.14  |  MaxDD: 4.2%  |  WinRate: 68%  ║
   ╚══════════════════════════════════════════════════╝
```

Display for 3 seconds, then collapse back to list view.

### 5.3 Transition Animations

#### Screen-to-Screen Transition

```
Pattern: Horizontal slide with brief overlap

Frame 0:  [Current screen at full opacity]
Frame 1:  [Current screen slides left, new screen enters from right, 30% visible]
Frame 2:  [Current screen 30% visible on left, new screen 70% visible]
Frame 3:  [New screen at full position]

Duration: 200ms total (3-4 frames at 60fps terminal refresh)
Easing: ease-out (fast start, gentle stop)
```

Fallback for slow terminals: instant swap with a 1-frame border flash.

#### Modal Popup

```
Entrance (150ms):
  Frame 0:  [dashboard normal]
  Frame 1:  [background dims 20% - overlay effect via muted bg-hover fill]
  Frame 2:  [modal box draws from center outward - scale up effect]
  Frame 3:  [modal at full size, content appears]

Exit (100ms):
  Frame 0:  [modal at full size]
  Frame 1:  [modal shrinks toward center]
  Frame 2:  [background returns to normal]
```

#### Tab Switching

```
Active tab has underline indicator that slides:

  [Workers]  [Queues]  [Strategies]  [Config]
   ────────

  User presses right arrow:

  [Workers]  [Queues]  [Strategies]  [Config]
              ────────                          <- underline slides right over 100ms
```

#### Loading Skeleton

While data loads, show placeholder blocks that pulse:

```
┌─ STRATEGIES ─────────────────────────────────┐
│                                               │
│  ░░░░░░░  ░░░░░░░░░░░░░░░  ░░░░  ░░░░░░     │  <- muted blocks pulse
│  ░░░░░░░  ░░░░░░░░░░░░░░░  ░░░░  ░░░░░░     │     between bg-surface
│  ░░░░░░░  ░░░░░░░░░░░░░░░  ░░░░  ░░░░░░     │     and bg-hover
│  ░░░░░░░  ░░░░░░░░░░░░░░░  ░░░░  ░░░░░░     │     over 1s cycle
│                                               │
└───────────────────────────────────────────────┘
```

### 5.4 Progress Indicators

#### Data Download Progress Bar

```
Full-width with ETA, speed, and percentage:

  Downloading ES historical data...
  ████████████████████████░░░░░░░░░░░░░░░░  62%  1.2 GB/s  ETA 0:34

Bar characters:
  Filled:    █
  Empty:     ░
  Head:      ▓  (leading edge, slightly different shade for motion feel)

Color: accent-primary fill, muted empty
```

#### Backtest Running Spinner

```
  Running backtest...  ◈  Walk-forward window 3/12  [████████░░░░]  67%

The diamond (◈) spins through: ◇ ◈ ◆ ◈
Step name updates as each phase completes.
```

#### Onboarding Step Progress

```
Dot-based (clean):
   ● ● ● ○ ○ ○
   Step 3 of 6: Select Data Source

Bar-based (detailed):
   ████████████████░░░░░░░░  Step 3/6: Select Data Source

Labeled (verbose, beginner mode):
   [1 Profile] -- [2 Broker] -- [3 Data] -- [ 4 Strategy ] -- [ 5 Risk ] -- [ 6 Review ]
       done          done       current        upcoming         upcoming       upcoming
```

### 5.5 Reduced Motion Mode

When `--no-animation` flag is set or `REDUCE_MOTION=true` env var:

| Normal Behavior | Reduced Motion |
|----------------|---------------|
| Typewriter text reveal | Instant text display |
| Sliding transitions | Instant screen swap |
| Pulsing indicators | Static colored indicators |
| Number ticking | Instant value update |
| Sparkline scroll | Static sparkline redraw |
| Modal scale animation | Instant show/hide |
| Boot sequence (2.5s) | Instant boot (show final state) |
| Celebration animation | Simple text notification |

---

## 6. Component Visual Specs

### 6.1 Worker Status Panel

#### Single Worker Card

```
┌─ RESEARCHER ───────────────────────── ● ACTIVE ─┐
│                                                  │
│  Session     2h 14m 32s                          │
│  Tasks       47 done, 3 running, 12 queued       │
│  Current     Generating YM momentum hypotheses   │
│  Last Out    hyp-20260209-014.json               │
│  Errors      0                                   │
│                                                  │
│  CPU  ████████████░░░░░░░░  58%                  │
│  MEM  ██████░░░░░░░░░░░░░░  32%                  │
│  PROG ████████████████░░░░  80%                  │
│                                                  │
└──────────────────────────────────────────────────┘
```

#### All Four Workers (Compact Dashboard View)

```
┌─ W O R K E R S ──────────────────────────────────────────────────────────────┐
│                                                                              │
│  ● RESEARCHER     ACTIVE   2h 14m   47 tasks   hyp-014.json    CPU 58%      │
│  ● BACKTESTER     ACTIVE   2h 14m   23 tasks   bt-042-v3.json  CPU 72%      │
│  ○ EVALUATOR      IDLE     --       --         eval-041.json   CPU  2%      │
│  ◐ PROMOTER       WAITING  0h 03m    0 tasks   --              CPU  1%      │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

#### Worker Status Colors

```
Status        Indicator    Color (Gotham)    Color (Neon)      Color (Knight)
------        ---------    --------------    -----------       --------------
ACTIVE        ● (solid)    #2ECC71 green     #39FF14 matrix    #50C878 emerald
IDLE          ○ (hollow)   #7E8A9A steel     #9B8FC2 violet    #555555 gray
WAITING       ◐ (half)     #F39C12 amber     #FFD700 gold      #FF8C00 orange
ERROR         ● (solid)    #E74C3C crimson   #FF3366 hot-pink  #DC143C crimson
SLEEPING      ◌ (dotted)   #4A5568 dark      #5C4F82 faded     #555555 gray
STARTING      ◈ (diamond)  #4FC1E9 cyan      #00FFFF e-cyan    #D4AF37 gold
```

### 6.2 Queue Dashboard

#### Full Queue Visualization

```
┌─ Q U E U E   D A S H B O A R D ─────────────────────────────────────────┐
│                                                                          │
│   HYPOTHESES          BACKTEST_Q          EVAL_Q          PROMOTION_Q    │
│   ┌────────┐          ┌────────┐          ┌────────┐      ┌────────┐    │
│   │ 12     │   >>>    │  8     │   >>>    │  4     │ >>>  │  0     │    │
│   │████████│          │██████  │          │████    │      │        │    │
│   │████████│          │██████  │          │████    │      │        │    │
│   │████████│          │██████  │          │        │      │        │    │
│   └────────┘          └────────┘          └────────┘      └────────┘    │
│   [warning]           [normal]            [normal]        [empty]       │
│                                                                          │
│   Throughput:  4.2 strat/hr    Avg backtest: 12m 34s    Pipeline: OK    │
│                                                                          │
│   [sparkline]  ▂▃▅▇█▇▅▃▂▃▅▇▃▅▇█▇▅▃▂▃▅▇▃▅▇█▇▅▃▂▃▅▇                    │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

#### Queue Depth Color Coding

```
Depth      Color           Visual
-----      -----           ------
0          muted           (empty)
1-4        success/green   ████
5-10       accent/cyan     ████████
11-15      warning/amber   ████████████
16+        error/red       ████████████████  <- also trigger alert icon
```

#### Flow Arrows

```
Standard:    >>>  or  -->  or  ->
Active:      >>>      (accent color, pulse if items flowing)
Idle:        ···      (muted, no flow)
Blocked:     >X>      (error color)
```

### 6.3 Strategy Card

#### Compact List View (One-Liner)

```
┌─ S T R A T E G I E S ───────────────────────────────────────────────────────┐
│                                                                              │
│  ID       NAME                  SHARPE   MAXDD    WIN%   STATUS             │
│  ─────────────────────────────────────────────────────────────────────────── │
│  STR-042  YM_ORB_Breakout       2.14     4.2%     68%    GOOD              │
│  STR-041  ES_MeanRev_v3         1.67     6.1%     61%    UNDER_REVIEW      │
│  STR-040  NQ_Momentum_fail      0.42    14.8%     43%    REJECTED          │
│  STR-039  GC_Counter_v2         1.89     5.3%     64%    TESTING           │
│  STR-038  ES_VWAP_Bounce        ---      ---      ---    QUEUED            │
│  STR-037  YM_Breakout_Lux       2.41     3.1%     71%    PROP_FIRM_READY   │
│                                                                              │
│  6 strategies  |  1 prop-ready  |  2 good  |  1 review  |  1 rejected       │
└──────────────────────────────────────────────────────────────────────────────┘
```

#### Status Color Coding

```
Status              Color (Gotham)     Icon    Description
------              --------------     ----    -----------
QUEUED              #7E8A9A muted      ○       Waiting in queue
TESTING             #4FC1E9 cyan       ◈       Backtest running
UNDER_REVIEW        #F39C12 amber      ◐       Evaluation in progress
GOOD                #2ECC71 green      ●       Passed evaluation
REJECTED            #E74C3C red        ✗       Failed evaluation
PROP_FIRM_READY     #D4AF37 gold       ★       Meets all prop firm criteria
ARCHIVED            #4A5568 dark       ◌       No longer active
```

#### Expanded Detail View (When User Selects a Strategy)

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  STR-042   YM_ORB_Breakout                                    ★ GOOD      ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  PERFORMANCE                          RISK METRICS                         ║
║  ──────────                           ────────────                         ║
║  Sharpe Ratio     2.14                Max Drawdown     4.2%                ║
║  Sortino Ratio    2.89                Avg Drawdown     1.8%                ║
║  Win Rate         68.3%               Recovery Time    2.1 days            ║
║  Profit Factor    1.94                Calmar Ratio     3.21                ║
║  Avg Win          $142.50             Daily VaR 95%    $312.00             ║
║  Avg Loss         $73.40              Max Consec Loss  4                   ║
║  Total Trades     847                                                      ║
║                                                                            ║
║  EQUITY CURVE (last 90 days)                                               ║
║  ──────────────────────────                                                ║
║  $12k ┤                                                    ╭──────         ║
║  $11k ┤                                            ╭───────╯               ║
║  $10k ┤                                    ╭───────╯                       ║
║   $9k ┤                        ╭───╮╭──────╯                               ║
║   $8k ┤            ╭───────────╯   ╰╯                                     ║
║   $7k ┤────────────╯                                                       ║
║                                                                            ║
║  PROP FIRM COMPLIANCE                                                      ║
║  ────────────────────                                                      ║
║   Apex         Max DD 6%    [████████████████████░]  4.2%   PASS          ║
║   TopStep      Max DD 5%    [████████████████░░░░░]  4.2%   PASS          ║
║   FTMO         Max DD 10%   [████████░░░░░░░░░░░░]  4.2%   PASS          ║
║   Earn2Trade   Max DD 5.5%  [███████████████░░░░░░]  4.2%   PASS          ║
║                                                                            ║
║  HYPOTHESIS ORIGIN                                                         ║
║  ────────────────                                                          ║
║  Generated: 2026-02-07 14:23 UTC                                           ║
║  Source: hyp-20260207-089.json                                             ║
║  Instrument: YM (Dow Jones Mini)                                           ║
║  Type: ORB Breakout with volatility filter                                 ║
║                                                                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  [p] Promote  [e] Export  [d] Details  [b] Back  [q] Quit                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

### 6.4 Onboarding Wizard

#### Welcome Screen

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│                                                                          │
│     ____  _                         ___                   _              │
│    / ___|(_) __ _ _ __ ___   __ _  / _ \ _   _  __ _ _ __ | |_           │
│    \___ \| |/ _` | '_ ` _ \ / _` || | | | | | |/ _` | '_ \| __|          │
│     ___) | | (_| | | | | | | (_| || |_| | |_| | (_| | | | | |_           │
│    |____/|_|\__, |_| |_| |_|\__,_| \__\_\\__,_|\__,_|_| |_|\__|          │
│             |___/                                                        │
│                                                                          │
│              Autonomous Strategy Research Factory                         │
│                                                                          │
│                                                                          │
│    Welcome, operator. Let's configure your research environment.         │
│                                                                          │
│                                                                          │
│    Choose your path:                                                     │
│                                                                          │
│      [1]  Quick Start    Sensible defaults, start in 60 seconds         │
│                                                                          │
│      [2]  Guided Setup   Step-by-step configuration (recommended)       │
│                                                                          │
│      [3]  Expert Mode    I know what I'm doing. Open config.json.       │
│                                                                          │
│                                                                          │
│    Press 1, 2, or 3 to continue...                                       │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

#### Step Indicator

```
Minimal (top of each screen):

  ── SETUP ───── ● ── ● ── ● ── ○ ── ○ ── ○ ─────
                 1    2    3    4    5    6
                              ▲
                          current
```

```
Labeled (beginner mode):

  ┌─ SETUP PROGRESS ──────────────────────────────────────────────────┐
  │                                                                    │
  │  [1]       [2]       [3]       [4]       [5]       [6]            │
  │ Profile   Broker    Data    Strategy    Risk     Review           │
  │   ●─────────●─────────●─────────○─────────○─────────○             │
  │  done      done    current                                        │
  │                                                                    │
  └────────────────────────────────────────────────────────────────────┘
```

#### Form Fields

```
Default (unfocused):
  ┌─────────────────────────────────────────────┐
  │  Data Source                                 │
  │  ┌───────────────────────────────────────┐   │
  │  │ databento                             │   │
  │  └───────────────────────────────────────┘   │
  │  [muted] Provider for historical OHLCV data  │
  └─────────────────────────────────────────────┘

Focused (active input):
  ┌─────────────────────────────────────────────┐
  │  [accent] Data Source                        │
  │  ┌───────────────────────────────────────┐   │  <- border turns accent color
  │  │ databento_                            │   │  <- cursor visible
  │  └───────────────────────────────────────┘   │
  │  [muted] Provider for historical OHLCV data  │
  └─────────────────────────────────────────────┘

Error:
  ┌─────────────────────────────────────────────┐
  │  [error] Data Source                         │
  │  ┌───────────────────────────────────────┐   │  <- border turns error color
  │  │ invalid_source                        │   │
  │  └───────────────────────────────────────┘   │
  │  [error] Unknown provider. Options:          │
  │          databento, polygon, csv             │
  └─────────────────────────────────────────────┘

Success (validated):
  ┌─────────────────────────────────────────────┐
  │  [success] Data Source  ✓                    │
  │  ┌───────────────────────────────────────┐   │
  │  │ databento                             │   │
  │  └───────────────────────────────────────┘   │
  │  [success] Connected and verified            │
  └─────────────────────────────────────────────┘
```

#### Select / Dropdown

```
  Instrument Selection
  ┌─────────────────────────────┐
  │  > ES   E-mini S&P 500     │  <- highlighted row (bg-hover + accent text)
  │    NQ   E-mini Nasdaq      │
  │    YM   E-mini Dow         │
  │    GC   Gold               │
  │    CL   Crude Oil          │
  └─────────────────────────────┘
  [muted] ↑↓ navigate  Enter select  Space multi-select
```

#### Completion Celebration Screen

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│                                                                          │
│                         ╔═══════════════════╗                             │
│                         ║   SETUP COMPLETE  ║                             │
│                         ╚═══════════════════╝                             │
│                                                                          │
│              ● ──── ● ──── ● ──── ● ──── ● ──── ●                       │
│              1      2      3      4      5      6                        │
│             [all dots filled, accent color]                               │
│                                                                          │
│                                                                          │
│    Configuration Summary:                                                │
│    ──────────────────────                                                │
│                                                                          │
│    Profile       production                                              │
│    Broker        tradovate                                               │
│    Data Source   databento                                                │
│    Instruments   ES, NQ, YM, GC                                          │
│    Risk Level    moderate                                                 │
│    Workers       4 (researcher, backtester, evaluator, promoter)         │
│                                                                          │
│    Config saved to: ~/.sigma-quant/config.json                           │
│                                                                          │
│                                                                          │
│    [accent] Press Enter to launch the dashboard...                       │
│    [muted]  Or press 'e' to edit configuration                           │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 6.5 Health Check Display

```
┌─ H E A L T H   C H E C K ───────────────────────────────────────────────┐
│                                                                          │
│   SYSTEM COMPONENT                  STATUS        DETAIL                 │
│   ────────────────────────────────────────────────────────────────────── │
│   ✓  Go Runtime                     PASS          go1.22.0               │
│   ✓  Bubble Tea TUI                 PASS          v1.2.4                 │
│   ✓  Redis / Queue Broker           PASS          Connected (3ms)        │
│   ✓  Data Provider (Databento)      PASS          API key valid          │
│   ✓  Config File                    PASS          ~/.sigma-quant/config  │
│   ✓  Output Directory               PASS          ./output/ (writable)   │
│   !  Disk Space                     WARN          12 GB free (< 20 GB)   │
│   ✓  Worker: Researcher             PASS          Registered             │
│   ✓  Worker: Backtester             PASS          Registered             │
│   ✓  Worker: Evaluator              PASS          Registered             │
│   ✓  Worker: Promoter               PASS          Registered             │
│   ✗  Freqtrade Bridge               FAIL          Not installed          │
│                                                                          │
│   ────────────────────────────────────────────────────────────────────── │
│   SUMMARY:  10 pass  |  1 warning  |  1 fail                            │
│                                                                          │
│   ████████████████████████████████████████████████░░░░░  10/12 checks    │
│   [green ████████████████████][amber ████][red ░░░░░]                    │
│                                                                          │
│   [muted] Freqtrade bridge is optional. Install with:                    │
│   [accent] pip install freqtrade                                         │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

#### Health Check Icon Styles

```
Pass:       ✓  (success color, bold)
Warning:    !  (warning color, bold)
Fail:       ✗  (error color, bold)
Skipped:    -  (muted color)
Running:    ◈  (accent color, spinning)
```

### 6.6 Command Palette / Help Modal

```
┌─ K E Y B O A R D   S H O R T C U T S ──────────────────────────────────┐
│                                                                          │
│   NAVIGATION                           ACTIONS                           │
│   ──────────                           ───────                           │
│   Tab        Next panel                Enter      Select/confirm         │
│   Shift+Tab  Previous panel            Esc        Back/cancel            │
│   ↑ ↓        Navigate within panel     Space      Toggle selection       │
│   ← →        Switch tabs               /          Search/filter          │
│   g          Go to... (jump menu)      r          Refresh data           │
│                                                                          │
│   VIEWS                                SYSTEM                            │
│   ─────                                ──────                            │
│   1          Dashboard                 h          Health check           │
│   2          Workers                   c          Configuration          │
│   3          Strategies                ?          This help screen       │
│   4          Queue monitor             q          Quit                   │
│   5          Logs                      Ctrl+C     Force quit             │
│                                                                          │
│   WORKER CONTROL                                                         │
│   ──────────────                                                         │
│   s          Start selected worker                                       │
│   p          Pause selected worker                                       │
│   x          Stop selected worker                                        │
│   R          Restart all workers                                         │
│                                                                          │
│   [muted] Press any key to close                                         │
└──────────────────────────────────────────────────────────────────────────┘
```

### 6.7 Log Viewer

```
┌─ L O G S ─────────────────────────────────── [auto-scroll: ON] ──────────┐
│                                                                          │
│  12:34:01  [INFO ]  researcher   Generating hypotheses for YM            │
│  12:34:02  [INFO ]  researcher   Found 3 candidate patterns              │
│  12:34:05  [INFO ]  researcher   Hypothesis hyp-014 queued               │
│  12:34:06  [DEBUG]  backtester   Picking up hyp-012 from queue           │
│  12:34:08  [INFO ]  backtester   Running walk-forward window 1/12        │
│  12:34:15  [INFO ]  backtester   Running walk-forward window 2/12        │
│  12:34:22  [WARN ]  backtester   Window 2 sharpe below threshold (0.8)   │
│  12:34:30  [INFO ]  backtester   Running walk-forward window 3/12        │
│  12:34:45  [INFO ]  backtester   Backtest complete: sharpe 1.67          │
│  12:34:46  [INFO ]  evaluator    Evaluating STR-041 (ES_MeanRev_v3)     │
│  12:34:48  [ERROR]  evaluator    Max drawdown exceeds limit: 14.8%       │
│  12:34:48  [INFO ]  evaluator    STR-040 REJECTED                        │
│                                                                          │
│  ─ Filter: [all] ──────────────── Level: [all] ── Worker: [all] ──────  │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

#### Log Level Colors

```
Level     Color (Gotham)     Color (Neon)       Color (Knight)
-----     --------------     -----------        --------------
DEBUG     #4A5568 muted      #5C4F82 faded      #555555 gray
INFO      #C8CED8 primary    #E0D7F5 lavender   #B8B8B8 silver
WARN      #F39C12 amber      #FFD700 gold       #FF8C00 orange
ERROR     #E74C3C crimson    #FF3366 hot-pink    #DC143C crimson
FATAL     #E74C3C bold+bg    #FF3366 bold+bg     #DC143C bold+bg
```

---

## 7. Responsive Design

### Breakpoint Strategy

```
NARROW        < 80 columns      Single column, stacked, abbreviated
STANDARD      80-119 columns    Two-column layout, full labels
WIDE          120+ columns      Four-column dashboard, full detail
```

### Narrow Layout (< 80 cols)

```
┌──────────────────────────────────────────┐
│  SQ  SIGMA-QUANT  v0.1.0    12:34 UTC   │
├──────────────────────────────────────────┤
│  WORKERS                                 │
│  ● RSRCH  ACTV  47t  CPU58%             │
│  ● BKTST  ACTV  23t  CPU72%             │
│  ○ EVAL   IDLE  --   CPU 2%             │
│  ◐ PROMO  WAIT   0t  CPU 1%             │
├──────────────────────────────────────────┤
│  QUEUES  hyp:12  bt:8  ev:4  pr:0       │
│  ▂▃▅▇█▇▅▃▂▃▅▇  4.2 strat/hr            │
├──────────────────────────────────────────┤
│  STRATEGIES (6)                          │
│  042 YM_ORB_Break  2.14 GOOD            │
│  041 ES_MeanRev    1.67 REVW            │
│  040 NQ_Mom_fail   0.42 REJD            │
│  039 GC_Counter    1.89 TEST            │
│  038 ES_VWAP_Bn    ---  QUED            │
│  037 YM_Break_Lux  2.41 PROP            │
├──────────────────────────────────────────┤
│  ? help  q quit  Tab nav                │
└──────────────────────────────────────────┘
```

Key narrow adaptations:
- Worker names abbreviated (RESEARCHER -> RSRCH, BACKTESTER -> BKTST)
- Status abbreviated (ACTIVE -> ACTV, UNDER_REVIEW -> REVW)
- Strategy names truncated with ellipsis
- Queue depths shown inline
- Sparklines compressed
- Single-column stacked layout
- Panels separated by horizontal rules instead of side-by-side

### Standard Layout (80-119 cols)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  SIGMA-QUANT STREAM                           v0.1.0    [12:34:05 UTC] │
├─────────────────────────────────┬───────────────────────────────────────┤
│  W O R K E R S                  │  Q U E U E S                         │
│                                 │                                       │
│  ● RESEARCHER   ACTIVE  47t    │  hypotheses     ████████░░░░  12      │
│  ● BACKTESTER   ACTIVE  23t    │  backtest_q     ██████░░░░░░   8      │
│  ○ EVALUATOR    IDLE    --     │  eval_q         ████░░░░░░░░   4      │
│  ◐ PROMOTER     WAITING  0t    │  promotion_q    ░░░░░░░░░░░░   0      │
│                                 │                                       │
├─────────────────────────────────┴───────────────────────────────────────┤
│  S T R A T E G I E S                                                    │
│                                                                         │
│  ID       NAME                  SHARPE   MAXDD   STATUS                 │
│  STR-042  YM_ORB_Breakout       2.14     4.2%    GOOD                  │
│  STR-041  ES_MeanRev_v3         1.67     6.1%    UNDER_REVIEW          │
│  STR-040  NQ_Momentum_fail      0.42    14.8%    REJECTED              │
│  STR-039  GC_Counter_v2         1.89     5.3%    TESTING               │
│  STR-038  ES_VWAP_Bounce        ---      ---     QUEUED                │
│  STR-037  YM_Breakout_Lux       2.41     3.1%    PROP_FIRM_READY       │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│  Throughput: 4.2 strat/hr  ▂▃▅▇█▇▅▃▂▃▅▇    Backtests: 12.8/hr        │
├─────────────────────────────────────────────────────────────────────────┤
│  ? help  |  q quit  |  Tab switch panel  |  1-5 jump to view           │
└─────────────────────────────────────────────────────────────────────────┘
```

### Wide Layout (120+ cols)

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  S I G M A - Q U A N T   S T R E A M                                                     v0.1.0    [12:34:05 UTC]  │
├──────────────────────────────┬──────────────────────────────┬─────────────────────────────┬───────────────────────────┤
│  W O R K E R S               │  Q U E U E S                 │  T H R O U G H P U T        │  S Y S T E M              │
│                              │                              │                             │                           │
│  ● RESEARCHER   ACTIVE       │  hypotheses    ████████  12  │  Strat/hr   4.2             │  CPU   ████░░░░  48%      │
│    Session: 2h 14m           │  backtest_q    ██████     8  │  ▂▃▅▇█▇▅▃▂▃▅▇              │  MEM   ██████░░  62%      │
│    Tasks: 47 done            │  eval_q        ████       4  │                             │  DISK  ████████  84%      │
│                              │  promotion_q   ░░         0  │  BT/hr     12.8             │  Uptime 2h 14m            │
│  ● BACKTESTER   ACTIVE       │                              │  ▃▅▇█▇▅▃▂▃▅▇█              │                           │
│    Session: 2h 14m           │  Total flow: 24 items        │                             │  Workers: 4/4             │
│    Tasks: 23 done            │  Avg latency: 34ms           │  Eval/hr    8.4             │  Queues: OK               │
│                              │                              │  ▅▇█▇▅▃▂▃▅▇▃▅              │  Health: NOMINAL          │
│  ○ EVALUATOR    IDLE         │                              │                             │                           │
│  ◐ PROMOTER     WAITING      │                              │                             │                           │
│                              │                              │                             │                           │
├──────────────────────────────┴──────────────────────────────┴─────────────────────────────┴───────────────────────────┤
│  S T R A T E G I E S                                                                                                 │
│                                                                                                                      │
│  ID       NAME                  SHARPE   SORTINO   MAXDD    WIN%    PF     TRADES   PROP FIRMS        STATUS         │
│  ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────── │
│  STR-042  YM_ORB_Breakout       2.14     2.89      4.2%     68%    1.94    847     Apex,TopStep      GOOD           │
│  STR-041  ES_MeanRev_v3         1.67     2.11      6.1%     61%    1.52    523     TopStep           UNDER_REVIEW   │
│  STR-040  NQ_Momentum_fail      0.42     0.58     14.8%     43%    0.87    312     --                REJECTED       │
│  STR-039  GC_Counter_v2         1.89     2.45      5.3%     64%    1.78    692     Apex,FTMO         TESTING        │
│  STR-038  ES_VWAP_Bounce        ---      ---       ---      ---    ---     ---     --                QUEUED         │
│  STR-037  YM_Breakout_Lux       2.41     3.12      3.1%     71%    2.14    1024    All 4             PROP_FIRM_RDY  │
│                                                                                                                      │
├──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│  ? help  |  q quit  |  Tab switch  |  1-5 views  |  / search  |  r refresh  |  s start  |  p pause  |  x stop       │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Responsive Adaptation Rules

| Element | Narrow (<80) | Standard (80-119) | Wide (120+) |
|---------|-------------|-------------------|-------------|
| Logo | `[SQ]` inline | `SIGMA-QUANT STREAM` | `S I G M A - Q U A N T   S T R E A M` |
| Worker names | 5-char abbrev | Full name | Full name + session details |
| Status labels | 4-char abbrev | Full word | Full word |
| Strategy names | Truncated 14ch | Full name | Full name |
| Columns | 1 | 2 | 4 |
| Sparklines | Hidden or 12ch | 16ch | 24ch |
| Keybind help | 3 items | 5 items | All items |
| Queue bars | Numeric only | Short bars | Full bars + labels |
| Strategy metrics | Sharpe only | Sharpe + MaxDD | All metrics |
| Prop firm col | Hidden | Status only | Firm names listed |

### Terminal Width Detection

```go
func getLayout(width int) Layout {
    switch {
    case width >= 120:
        return LayoutWide
    case width >= 80:
        return LayoutStandard
    default:
        return LayoutNarrow
    }
}
```

---

## 8. Accessibility Considerations

### 8.1 High Contrast Mode

Activated via `--high-contrast` flag or `SIGMA_HIGH_CONTRAST=true` env var.

```
Standard Mode                    High Contrast Mode
─────────────                    ──────────────────
bg-primary    #0B0E14            bg-primary    #000000
text-primary  #C8CED8            text-primary  #FFFFFF
text-muted    #4A5568            text-muted    #999999
accent        #4FC1E9            accent        #00FFFF
border        #2A3444            border        #FFFFFF
```

All text meets WCAG AAA (7:1 contrast ratio) in high contrast mode.

### 8.2 Colorblind-Safe Variants

Since the interface uses red/green status coding, provide alternatives:

```
MODE              PASS          WARN          FAIL          INFO
────              ────          ────          ────          ────
Normal            Green ●       Amber ●       Red ●         Cyan ●
Deuteranopia      Blue ●        Yellow ●      Orange ●      Cyan ●
Protanopia        Blue ●        Yellow ●      Orange ●      Cyan ●
Tritanopia        Green ●       Pink ●        Red ●         Blue ●

Enable: --colorblind=deuteranopia | protanopia | tritanopia
```

Additionally, never convey information by color alone. Every colored indicator also has:
- A distinct icon (checkmark vs exclamation vs X)
- A text label (PASS, WARN, FAIL)
- A positional cue (pass items grouped separately from fail items)

### 8.3 Screen Reader Compatibility

While TUI apps have limited screen reader support, we provide:

1. **Structured output mode**: `--accessible` flag renders plain text with clear section headers, no box-drawing characters, no color codes
2. **Status announcements**: Key state changes printed as plain text lines that screen readers can catch
3. **Tab order**: Logical left-to-right, top-to-bottom focus order

Accessible mode output example:

```
== SIGMA-QUANT STATUS ==

WORKERS:
  Researcher: ACTIVE, 47 tasks completed
  Backtester: ACTIVE, 23 tasks completed
  Evaluator: IDLE
  Promoter: WAITING

QUEUES:
  hypotheses: 12 items
  backtest_q: 8 items
  eval_q: 4 items
  promotion_q: 0 items

STRATEGIES:
  STR-042 YM_ORB_Breakout Sharpe:2.14 Status:GOOD
  STR-041 ES_MeanRev_v3 Sharpe:1.67 Status:UNDER_REVIEW
  ...
```

### 8.4 Reduced Motion

See Section 5.5 for full reduced motion specification.

### 8.5 Font Size

Terminal font size is controlled by the user's terminal emulator. The TUI should:
- Never assume a specific font size
- Use relative spacing (character counts, not pixels)
- Test at 10pt, 14pt, and 18pt minimum
- Ensure all content is visible without horizontal scrolling at 80 cols

---

## 9. Lipgloss Implementation Guide

### 9.1 Theme Structure

```go
package theme

import "github.com/charmbracelet/lipgloss"

// Theme defines all colors and styles for the application.
type Theme struct {
    Name string

    // Backgrounds
    BgPrimary   lipgloss.Color
    BgSecondary lipgloss.Color
    BgSurface   lipgloss.Color
    BgHover     lipgloss.Color

    // Text
    TextPrimary   lipgloss.Color
    TextSecondary lipgloss.Color
    TextMuted     lipgloss.Color
    TextAccent    lipgloss.Color

    // Accents
    AccentPrimary   lipgloss.Color
    AccentSuccess   lipgloss.Color
    AccentWarning   lipgloss.Color
    AccentError     lipgloss.Color
    AccentInfo      lipgloss.Color
    AccentHighlight lipgloss.Color

    // Borders
    BorderPrimary lipgloss.Color
    BorderActive  lipgloss.Color
    BorderMuted   lipgloss.Color
}

// GothamNight is Palette 1: deep blues, ice cyan, professional.
var GothamNight = Theme{
    Name:            "gotham-night",
    BgPrimary:       lipgloss.Color("#0B0E14"),
    BgSecondary:     lipgloss.Color("#121821"),
    BgSurface:       lipgloss.Color("#1A2130"),
    BgHover:         lipgloss.Color("#222D3F"),
    TextPrimary:     lipgloss.Color("#C8CED8"),
    TextSecondary:   lipgloss.Color("#7E8A9A"),
    TextMuted:       lipgloss.Color("#4A5568"),
    TextAccent:      lipgloss.Color("#4FC1E9"),
    AccentPrimary:   lipgloss.Color("#4FC1E9"),
    AccentSuccess:   lipgloss.Color("#2ECC71"),
    AccentWarning:   lipgloss.Color("#F39C12"),
    AccentError:     lipgloss.Color("#E74C3C"),
    AccentInfo:      lipgloss.Color("#3498DB"),
    AccentHighlight: lipgloss.Color("#6C5CE7"),
    BorderPrimary:   lipgloss.Color("#2A3444"),
    BorderActive:    lipgloss.Color("#4FC1E9"),
    BorderMuted:     lipgloss.Color("#1E2836"),
}

// NeonOps is Palette 2: cyberpunk purple, electric cyan + magenta.
var NeonOps = Theme{
    Name:            "neon-ops",
    BgPrimary:       lipgloss.Color("#0D0221"),
    BgSecondary:     lipgloss.Color("#150734"),
    BgSurface:       lipgloss.Color("#1B0A45"),
    BgHover:         lipgloss.Color("#251258"),
    TextPrimary:     lipgloss.Color("#E0D7F5"),
    TextSecondary:   lipgloss.Color("#9B8FC2"),
    TextMuted:       lipgloss.Color("#5C4F82"),
    TextAccent:      lipgloss.Color("#00FFFF"),
    AccentPrimary:   lipgloss.Color("#00FFFF"),
    AccentSuccess:   lipgloss.Color("#39FF14"),
    AccentWarning:   lipgloss.Color("#FFD700"),
    AccentError:     lipgloss.Color("#FF3366"),
    AccentInfo:      lipgloss.Color("#7B68EE"),
    AccentHighlight: lipgloss.Color("#FF00FF"),
    BorderPrimary:   lipgloss.Color("#2D1B69"),
    BorderActive:    lipgloss.Color("#00FFFF"),
    BorderMuted:     lipgloss.Color("#1A0D3D"),
}

// DarkKnight is Palette 3: true black, gold accents, luxury.
var DarkKnight = Theme{
    Name:            "dark-knight",
    BgPrimary:       lipgloss.Color("#000000"),
    BgSecondary:     lipgloss.Color("#0A0A0A"),
    BgSurface:       lipgloss.Color("#141414"),
    BgHover:         lipgloss.Color("#1E1E1E"),
    TextPrimary:     lipgloss.Color("#D4AF37"),
    TextSecondary:   lipgloss.Color("#B8B8B8"),
    TextMuted:       lipgloss.Color("#555555"),
    TextAccent:      lipgloss.Color("#FFD700"),
    AccentPrimary:   lipgloss.Color("#D4AF37"),
    AccentSuccess:   lipgloss.Color("#50C878"),
    AccentWarning:   lipgloss.Color("#FF8C00"),
    AccentError:     lipgloss.Color("#DC143C"),
    AccentInfo:      lipgloss.Color("#708090"),
    AccentHighlight: lipgloss.Color("#D4AF37"),
    BorderPrimary:   lipgloss.Color("#1E1E1E"),
    BorderActive:    lipgloss.Color("#D4AF37"),
    BorderMuted:     lipgloss.Color("#0F0F0F"),
}
```

### 9.2 Component Style Definitions

```go
package styles

import "github.com/charmbracelet/lipgloss"

// Styles holds all pre-computed lipgloss styles for the active theme.
type Styles struct {
    theme Theme

    // Layout
    App           lipgloss.Style
    TitleBar      lipgloss.Style
    StatusBar     lipgloss.Style
    Panel         lipgloss.Style
    PanelActive   lipgloss.Style

    // Text
    H1            lipgloss.Style
    H2            lipgloss.Style
    H3            lipgloss.Style
    Body          lipgloss.Style
    Muted         lipgloss.Style
    Accent        lipgloss.Style

    // Components
    WorkerCard    lipgloss.Style
    QueueBar      lipgloss.Style
    StrategyRow   lipgloss.Style
    StrategyCard  lipgloss.Style
    Modal         lipgloss.Style
    FormField     lipgloss.Style
    FormFieldFocus lipgloss.Style
    FormFieldError lipgloss.Style

    // Status indicators
    StatusActive  lipgloss.Style
    StatusIdle    lipgloss.Style
    StatusWarning lipgloss.Style
    StatusError   lipgloss.Style
    StatusSuccess lipgloss.Style
}

// NewStyles creates all styles for a given theme.
func NewStyles(t Theme) Styles {
    s := Styles{theme: t}

    // ── Layout ──────────────────────────────────────────────

    s.App = lipgloss.NewStyle().
        Background(t.BgPrimary).
        Foreground(t.TextPrimary)

    s.TitleBar = lipgloss.NewStyle().
        Background(t.BgSecondary).
        Foreground(t.TextAccent).
        Bold(true).
        Padding(0, 2).
        MarginBottom(1)

    s.StatusBar = lipgloss.NewStyle().
        Background(t.BgSecondary).
        Foreground(t.TextMuted).
        Padding(0, 2).
        MarginTop(1)

    s.Panel = lipgloss.NewStyle().
        Border(lipgloss.RoundedBorder()).
        BorderForeground(t.BorderPrimary).
        Background(t.BgSecondary).
        Foreground(t.TextPrimary).
        Padding(1, 2)

    s.PanelActive = s.Panel.
        BorderForeground(t.BorderActive)

    // ── Typography ──────────────────────────────────────────

    s.H1 = lipgloss.NewStyle().
        Foreground(t.TextAccent).
        Bold(true).
        MarginBottom(1)

    s.H2 = lipgloss.NewStyle().
        Foreground(t.TextPrimary).
        Bold(true)

    s.H3 = lipgloss.NewStyle().
        Foreground(t.TextSecondary)

    s.Body = lipgloss.NewStyle().
        Foreground(t.TextPrimary)

    s.Muted = lipgloss.NewStyle().
        Foreground(t.TextMuted)

    s.Accent = lipgloss.NewStyle().
        Foreground(t.TextAccent)

    // ── Components ──────────────────────────────────────────

    s.WorkerCard = lipgloss.NewStyle().
        Border(lipgloss.RoundedBorder()).
        BorderForeground(t.BorderPrimary).
        Background(t.BgSecondary).
        Padding(1, 2).
        Width(46)

    s.QueueBar = lipgloss.NewStyle().
        Foreground(t.AccentPrimary).
        Background(t.BgSurface)

    s.StrategyRow = lipgloss.NewStyle().
        Foreground(t.TextPrimary).
        Padding(0, 1)

    s.StrategyCard = lipgloss.NewStyle().
        Border(lipgloss.DoubleBorder()).
        BorderForeground(t.BorderActive).
        Background(t.BgSecondary).
        Padding(1, 2).
        MarginTop(1).
        MarginBottom(1)

    s.Modal = lipgloss.NewStyle().
        Border(lipgloss.DoubleBorder()).
        BorderForeground(t.BorderActive).
        Background(t.BgSurface).
        Padding(2, 4).
        Align(lipgloss.Center)

    s.FormField = lipgloss.NewStyle().
        Border(lipgloss.RoundedBorder()).
        BorderForeground(t.BorderPrimary).
        Padding(0, 1).
        MarginBottom(1)

    s.FormFieldFocus = s.FormField.
        BorderForeground(t.AccentPrimary)

    s.FormFieldError = s.FormField.
        BorderForeground(t.AccentError)

    // ── Status Indicators ───────────────────────────────────

    s.StatusActive = lipgloss.NewStyle().
        Foreground(t.AccentSuccess).
        Bold(true)

    s.StatusIdle = lipgloss.NewStyle().
        Foreground(t.TextSecondary)

    s.StatusWarning = lipgloss.NewStyle().
        Foreground(t.AccentWarning).
        Bold(true)

    s.StatusError = lipgloss.NewStyle().
        Foreground(t.AccentError).
        Bold(true)

    s.StatusSuccess = lipgloss.NewStyle().
        Foreground(t.AccentSuccess)

    return s
}
```

### 9.3 Dynamic Width Handling

```go
package layout

import (
    "github.com/charmbracelet/lipgloss"
    tea "github.com/charmbracelet/bubbletea"
)

type Layout int

const (
    LayoutNarrow   Layout = iota // < 80
    LayoutStandard               // 80-119
    LayoutWide                   // 120+
)

func DetectLayout(msg tea.WindowSizeMsg) Layout {
    switch {
    case msg.Width >= 120:
        return LayoutWide
    case msg.Width >= 80:
        return LayoutStandard
    default:
        return LayoutNarrow
    }
}

// PanelWidths returns column widths for the current layout.
func PanelWidths(layout Layout, totalWidth int) []int {
    switch layout {
    case LayoutWide:
        // 4 equal columns with gaps
        col := (totalWidth - 6) / 4 // 6 = 3 gaps * 2 chars
        return []int{col, col, col, col}
    case LayoutStandard:
        // 2 columns
        col := (totalWidth - 2) / 2
        return []int{col, col}
    default:
        // single column
        return []int{totalWidth}
    }
}

// AdaptPanel adjusts a panel style to the available width.
func AdaptPanel(base lipgloss.Style, width int) lipgloss.Style {
    return base.Width(width)
}
```

### 9.4 Progress Bar Component

```go
package components

import "github.com/charmbracelet/lipgloss"

type ProgressBar struct {
    Width      int
    Percent    float64
    Filled     lipgloss.Style
    Empty      lipgloss.Style
    ShowLabel  bool
}

func NewProgressBar(theme Theme, width int) ProgressBar {
    return ProgressBar{
        Width: width,
        Filled: lipgloss.NewStyle().
            Foreground(theme.AccentPrimary).
            SetString("█"),
        Empty: lipgloss.NewStyle().
            Foreground(theme.BorderMuted).
            SetString("░"),
        ShowLabel: true,
    }
}

func (p ProgressBar) Render(percent float64) string {
    filled := int(float64(p.Width) * percent)
    if filled > p.Width {
        filled = p.Width
    }

    bar := ""
    for i := 0; i < p.Width; i++ {
        if i < filled {
            bar += p.Filled.String()
        } else {
            bar += p.Empty.String()
        }
    }

    if p.ShowLabel {
        label := lipgloss.NewStyle().
            Foreground(lipgloss.Color("#C8CED8")).
            Render(fmt.Sprintf(" %3.0f%%", percent*100))
        bar += label
    }

    return bar
}
```

### 9.5 Sparkline Component

```go
package components

import "github.com/charmbracelet/lipgloss"

var sparkBlocks = []rune{'▁', '▂', '▃', '▄', '▅', '▆', '▇', '█'}

type Sparkline struct {
    Width int
    Color lipgloss.Style
    Data  []float64
}

func NewSparkline(theme Theme, width int) Sparkline {
    return Sparkline{
        Width: width,
        Color: lipgloss.NewStyle().Foreground(theme.AccentPrimary),
    }
}

func (s Sparkline) Render(data []float64) string {
    if len(data) == 0 {
        return ""
    }

    // Normalize data to 0-7 range
    min, max := data[0], data[0]
    for _, v := range data {
        if v < min { min = v }
        if v > max { max = v }
    }

    spread := max - min
    if spread == 0 {
        spread = 1
    }

    // Take last N points to fit width
    start := 0
    if len(data) > s.Width {
        start = len(data) - s.Width
    }

    result := ""
    for i := start; i < len(data); i++ {
        normalized := (data[i] - min) / spread
        idx := int(normalized * 7)
        if idx > 7 { idx = 7 }
        result += string(sparkBlocks[idx])
    }

    return s.Color.Render(result)
}
```

### 9.6 Worker Status Indicator

```go
package components

import "github.com/charmbracelet/lipgloss"

type WorkerStatus int

const (
    WorkerActive WorkerStatus = iota
    WorkerIdle
    WorkerWaiting
    WorkerError
    WorkerSleeping
    WorkerStarting
)

type StatusIndicator struct {
    theme Theme
}

func (si StatusIndicator) Render(status WorkerStatus) string {
    switch status {
    case WorkerActive:
        return lipgloss.NewStyle().
            Foreground(si.theme.AccentSuccess).
            Bold(true).
            Render("●")
    case WorkerIdle:
        return lipgloss.NewStyle().
            Foreground(si.theme.TextSecondary).
            Render("○")
    case WorkerWaiting:
        return lipgloss.NewStyle().
            Foreground(si.theme.AccentWarning).
            Render("◐")
    case WorkerError:
        return lipgloss.NewStyle().
            Foreground(si.theme.AccentError).
            Bold(true).
            Render("●")
    case WorkerSleeping:
        return lipgloss.NewStyle().
            Foreground(si.theme.TextMuted).
            Render("◌")
    case WorkerStarting:
        return lipgloss.NewStyle().
            Foreground(si.theme.AccentPrimary).
            Render("◈")
    default:
        return "?"
    }
}

func (si StatusIndicator) Label(status WorkerStatus) string {
    labels := map[WorkerStatus]string{
        WorkerActive:   "ACTIVE",
        WorkerIdle:     "IDLE",
        WorkerWaiting:  "WAITING",
        WorkerError:    "ERROR",
        WorkerSleeping: "SLEEPING",
        WorkerStarting: "STARTING",
    }
    return labels[status]
}
```

### 9.7 Border Variants

```go
// Standard panel border (most common)
lipgloss.RoundedBorder()
// Result: ╭─────╮
//         │     │
//         ╰─────╯

// Active/focused panel
lipgloss.RoundedBorder() with BorderForeground(theme.BorderActive)
// Same shape, accent color

// Strategy detail card / modals (emphasis)
lipgloss.DoubleBorder()
// Result: ╔═════╗
//         ║     ║
//         ╚═════╝

// Neon Ops theme: heavy borders for that cyberpunk feel
lipgloss.ThickBorder()
// Result: ┏━━━━━┓
//         ┃     ┃
//         ┗━━━━━┛

// Minimal separators (between rows, sections)
lipgloss.NormalBorder() with only Border(true, false, false, false) // top only
// Result: ─────────

// No border (inline elements)
lipgloss.NewStyle().Padding(0, 1)
```

---

## 10. Dual Experience Mode

### 10.1 Expert Mode

For power users who know the system. Maximum information density.

```
Characteristics:
- Dense panel layout, minimal padding
- All keyboard shortcuts visible in status bar
- No tooltips or contextual help
- Abbreviated labels where possible
- Sparklines and charts always visible
- Log panel always accessible
- Fast animations (50% of normal duration)
```

Expert Mode Dashboard:

```
┌─SQ─v0.1.0──12:34:05──────────────────────────────────────────────────┐
│ ●RSRCH 47t ●BKTST 23t ○EVAL -- ◐PROMO 0t │ H:12 B:8 E:4 P:0      │
├─STRAT──────────────────────────────────────────────────────────────────┤
│ 042 YM_ORB_Break  2.14/2.89  4.2% 68% 1.94  GOOD   Apex,TS          │
│ 041 ES_MeanRev    1.67/2.11  6.1% 61% 1.52  REVW   TS               │
│ 040 NQ_Mom_fail   0.42/0.58 14.8% 43% 0.87  REJD   --               │
│>039 GC_Counter    1.89/2.45  5.3% 64% 1.78  TEST   Apex,FTMO        │
│ 038 ES_VWAP_Bn    ---        ---  --- ---   QUED   --               │
│ 037 YM_Break_Lux  2.41/3.12  3.1% 71% 2.14  PROP   All              │
├─THR──▂▃▅▇█▇▅▃▂▃▅▇─4.2s/h──BT──▃▅▇█▇▅▃▂▃▅▇█─12.8/h───CPU48%─M62%──┤
│ 12:34:48 [E] evaluator  STR-040 REJECTED (maxDD 14.8%)               │
│ 12:34:46 [I] evaluator  Evaluating STR-041                           │
│ 12:34:45 [I] backtester Backtest complete: sharpe 1.67               │
├─?─q─Tab─1-5─/─r─s─p─x─R─────────────────────────────────────────────┤
└───────────────────────────────────────────────────────────────────────┘
```

### 10.2 Beginner Mode

For new users. Guided, spacious, helpful.

```
Characteristics:
- Generous padding and spacing
- Full labels, no abbreviations
- Contextual tooltips on focused elements
- Step-by-step prompts for actions
- Confirmation dialogs for destructive actions
- Slower animations (100% of normal duration)
- Help panel visible by default on first run
- Onboarding tips that dismiss after first use
```

Beginner Mode Dashboard:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│   SIGMA-QUANT STREAM                              v0.1.0                 │
│   Autonomous Strategy Research Factory                                   │
│                                                                          │
│   Current Time: 12:34:05 UTC             Uptime: 2 hours 14 minutes     │
│                                                                          │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   WORKERS                                                                │
│   These are the AI agents running your research pipeline.                │
│                                                                          │
│   ● Researcher     Active     47 tasks completed                         │
│     Generates trading hypotheses from market data patterns.              │
│                                                                          │
│   ● Backtester     Active     23 tasks completed                         │
│     Tests hypotheses against historical data.                            │
│                                                                          │
│   ○ Evaluator      Idle       Waiting for backtests to finish            │
│     Grades strategies on risk-adjusted performance.                      │
│                                                                          │
│   ◐ Promoter       Waiting    No strategies ready for promotion          │
│     Checks if strategies meet prop firm requirements.                    │
│                                                                          │
│                                                                          │
│   TIP: Press 's' on a worker to start it, 'p' to pause.                 │
│                                                                          │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   STRATEGIES                                                             │
│   Your pipeline has produced 6 strategies so far.                        │
│                                                                          │
│   > STR-042  YM ORB Breakout         Sharpe: 2.14    Status: GOOD       │
│     Press Enter to see full details for this strategy.                   │
│                                                                          │
│     STR-041  ES Mean Reversion v3    Sharpe: 1.67    Under Review       │
│     STR-040  NQ Momentum             Sharpe: 0.42    Rejected           │
│     STR-039  GC Counter Trend v2     Sharpe: 1.89    Testing            │
│                                                                          │
│                                                                          │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   KEYBOARD SHORTCUTS                                                     │
│                                                                          │
│   Tab          Move to next panel                                        │
│   Up/Down      Navigate within a panel                                   │
│   Enter        Select or expand                                          │
│   ?            Show all shortcuts                                        │
│   q            Quit Sigma-Quant                                          │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 10.3 Mode Switching

```
Activation:
  CLI flag:       sigma-quant start --mode=expert
                  sigma-quant start --mode=beginner

  Runtime toggle: Press Ctrl+M to switch modes
                  (displays brief "Switched to Expert Mode" toast)

  Config file:    { "ui_mode": "expert" }   in config.json

  First run:      Defaults to beginner, asks after 1 hour of use:
                  "You seem comfortable. Switch to Expert Mode? [y/n]"
```

### 10.4 Mode Comparison Matrix

```
+------------------------+-------------------+----------------------+
|  Feature               |  Beginner Mode    |  Expert Mode         |
+------------------------+-------------------+----------------------+
|  Panel padding         |  2 lines top/bot  |  0-1 line            |
|  Label style           |  Full words       |  Abbreviated         |
|  Worker descriptions   |  Shown            |  Hidden              |
|  Tooltips              |  On focus          |  Hidden              |
|  Confirm destructive   |  Yes              |  No                  |
|  Keybind display       |  Labeled, footer  |  Compact, status bar |
|  Sparklines            |  Hidden           |  Always visible      |
|  Log panel             |  Hidden (toggle)  |  Always visible      |
|  Animation speed       |  100%             |  50%                 |
|  First-run tips        |  Yes              |  No                  |
|  Information density   |  Low              |  Maximum             |
|  Strategy metrics      |  Sharpe + status  |  All 7 metrics       |
|  Onboarding on start   |  Full wizard      |  Skip to dashboard   |
+------------------------+-------------------+----------------------+
```

---

## Appendix A: Box-Drawing Character Reference

```
Rounded:    ╭ ─ ╮ │ ╰ ╯
Double:     ╔ ═ ╗ ║ ╚ ╝
Heavy:      ┏ ━ ┓ ┃ ┗ ┛
Normal:     ┌ ─ ┐ │ └ ┘
Dashed:     ┌ ╌ ┐ ╎ └ ╌ ┘

Intersections:
  ├ ┤ ┬ ┴ ┼        (normal)
  ╠ ╣ ╦ ╩ ╬        (double)
  ┣ ┫ ┳ ┻ ╋        (heavy)

Bar blocks:
  Full:     █ ▉ ▊ ▋ ▌ ▍ ▎ ▏
  Height:   ▁ ▂ ▃ ▄ ▅ ▆ ▇ █
  Shade:    ░ ▒ ▓ █

Indicators:
  Circles:  ● ○ ◐ ◑ ◒ ◓ ◌ ◉
  Diamonds: ◇ ◈ ◆
  Arrows:   → ← ↑ ↓ ↗ ↘ ↙ ↖
  Checks:   ✓ ✗ ✕ ✔ ✘
  Stars:    ★ ☆ ✦ ✧
  Other:    ▸ ▹ ▴ ▾ ● ■ □
```

## Appendix B: Full Color Reference Table

```
+-------------------+-------------------+-------------------+-------------------+
|  Token            |  Gotham Night     |  Neon Ops         |  Dark Knight      |
+-------------------+-------------------+-------------------+-------------------+
|  bg-primary       |  #0B0E14          |  #0D0221          |  #000000          |
|  bg-secondary     |  #121821          |  #150734          |  #0A0A0A          |
|  bg-surface       |  #1A2130          |  #1B0A45          |  #141414          |
|  bg-hover         |  #222D3F          |  #251258          |  #1E1E1E          |
|  text-primary     |  #C8CED8          |  #E0D7F5          |  #D4AF37          |
|  text-secondary   |  #7E8A9A          |  #9B8FC2          |  #B8B8B8          |
|  text-muted       |  #4A5568          |  #5C4F82          |  #555555          |
|  text-accent      |  #4FC1E9          |  #00FFFF          |  #FFD700          |
|  accent-primary   |  #4FC1E9          |  #00FFFF          |  #D4AF37          |
|  accent-success   |  #2ECC71          |  #39FF14          |  #50C878          |
|  accent-warning   |  #F39C12          |  #FFD700          |  #FF8C00          |
|  accent-error     |  #E74C3C          |  #FF3366          |  #DC143C          |
|  accent-info      |  #3498DB          |  #7B68EE          |  #708090          |
|  accent-highlight |  #6C5CE7          |  #FF00FF          |  #D4AF37          |
|  border-primary   |  #2A3444          |  #2D1B69          |  #1E1E1E          |
|  border-active    |  #4FC1E9          |  #00FFFF          |  #D4AF37          |
|  border-muted     |  #1E2836          |  #1A0D3D          |  #0F0F0F          |
+-------------------+-------------------+-------------------+-------------------+
```

## Appendix C: Terminal Emulator Recommendations

For the best experience with Sigma-Quant Stream:

| Terminal | Platform | True Color | Nerd Fonts | Recommended |
|----------|----------|------------|------------|-------------|
| **WezTerm** | All | Yes | Built-in | First choice |
| **Ghostty** | macOS/Linux | Yes | Yes | First choice |
| **Kitty** | macOS/Linux | Yes | Yes | Excellent |
| **Alacritty** | All | Yes | Manual | Good |
| **iTerm2** | macOS | Yes | Manual | Good |
| **Windows Terminal** | Windows | Yes | Manual | Good |
| Terminal.app | macOS | 256 only | No | Not recommended |
| cmd.exe | Windows | No | No | Not supported |

Minimum requirements:
- True color (24-bit) support
- Unicode box-drawing characters
- Minimum 80 columns, 24 rows
- Monospace font with Nerd Font glyphs (optional but recommended)

## Appendix D: Design Decision Log

| Decision | Rationale |
|----------|-----------|
| Rounded borders for panels | Feels modern and premium vs sharp corners |
| Double borders for modals | Creates visual hierarchy, modal feels elevated |
| Letter-spaced H1 headers | Gotham/tech aesthetic, immediately recognizable |
| 2.5s boot sequence | Long enough to feel intentional, short enough not to annoy |
| Gold for PROP_FIRM_READY | Gold = achievement, stands out from green = good |
| Muted help in status bar | Discoverable but not distracting for experts |
| Three palette options | Gives user agency, covers professional-to-flashy spectrum |
| Sparklines for throughput | Trend matters more than exact values for monitoring |
| Pulse animation for active | Creates sense of a living, breathing system |
| Celebration on promotion | Positive reinforcement, makes pipeline feel rewarding |

---

*End of Visual Design System*
*Choose your palette. Build the command bridge.*
