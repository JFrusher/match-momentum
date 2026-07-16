This design represents an exceptionally fast and highly optimized workflow for tagging live sports events on a laptop. Tracing a physical vector path of the ball, using held modifier keys to specify actions, and then typing a sequence of numbers (the "passcode" pattern) during play stoppages is a stellar approach.

Below is the complete **Product Requirement Document (PRD) and MVP Specification** for your rugby momentum tracker.

---

# Product Requirement Document (PRD): Rugby Momentum Vector Tracker (MVP)

## 1. Project Overview & Objective

The **Rugby Momentum Vector Tracker** is a desktop application designed to capture live rugby match play-by-play data via a continuous vector-tracing interface.

The application translates live human tracing on a pitch coordinate system into discrete, relational JSON events. It leverages a **"Trace Now, Attribute Later"** workflow to allow a single user to track high-velocity gameplay without looking away from the pitch.

---

## 2. Key User Workflows (UX/UI Spec)

### A. Phase 1: Pre-Match Setup

Before the whistle blows, the user completes a quick, minimum setup screen:

1. **Match Metadata:** Team A (e.g., England) vs. Team B (e.g., New Zealand).
2. **Team Sheet Numbers:** A simple 1-15 number-to-player mapping table. If names are unknown, numbers default to generic placeholders (e.g., `"ENG 10"`).

### B. Phase 2: Live Tracing (The Ball-Vector System)

The user traces the physical path of the ball using their right hand on the mouse (or trackpad) and their left hand resting on the hotkey zone (`W-E-Q-A-Space`).

```
  [Mouse Down + Key Held] ────> [Drag Cursor] ────> [Mouse Release]
     Action Begins              Traces Path          Action Ends

```

* **Continuous Snap (Auto-Join):** If an action begins within $1000$ milliseconds of the previous action's release, the start coordinate of the new line automatically snaps to the exact end coordinate of the previous line.
* **Action Key Mapping:**
* `W` (Held) + Drag: **Carry / Run** (Draws a solid line).
* `E` (Held) + Drag: **Pass** (Draws a dashed line).
* `Q` (Held) + Drag: **Kick** (Draws an arrow line). *Automatically flags the receiving node as the opposing team.*
* `A` (Tap): **Tackle / Ruck** (Logs a point event and **terminates the play sequence**).



### C. Phase 3: The "Passcode" Annotation Overlay (Post-Play)

Tapping `A` (Ruck/Tackle) or `Space` (Whistle/Stoppage) immediately triggers a pause. The vector lines drawn during the play freeze on screen, and the software overlays sequential numerical input bubbles at every vector junction.

```
       [9]                      [10]                     [12]
 (Start of Pass) ────────── (Pass Caught) ────────── (Tackle Point)

```

1. **Auto-Focus Flow:** The cursor focuses on Bubble 1.
2. **Rapid Input:** The user types `9`, presses `Tab` (or the app auto-advances), types `10`, `Tab`, types `12`.
3. **Save & Clear:** Pressing `Enter` commits the fully attributed events to memory and clears the canvas, ready for the next kickoff or restart.

---

## 3. Dealing with Complex Rugby Mechanics

### Intercepts & Turnovers

* **The Intercept Modifier (`Shift` or `I`):** If a pass is drawn from England $10 \to 12$, but a New Zealand defender intercepts it mid-flight, the user hits `Shift` (or `I`) before releasing the mouse.
* **Behavior:** The recipient node is automatically assigned to the opposing team. During the passcode phase, the bubble prompts for the intercepting player's number.

### Unidentified Players (The Anonymous Escape Hatch)

* If the user cannot read a jersey number on the broadcast, they simply press `Space` or leave the passcode bubble blank.
* **Behavior:** The database writes the event with an `"anonymous"` player tag, preserving the spatial and momentum data of the play without halting the user.

---

## 4. System Architecture & Technical Stack

```
┌─────────────────────────────────────────────────────────────┐
│                       NiceGUI Frontend                      │
│  - ui.interactive_image (Pitch Background)                 │
│  - SVG Overlay (Dynamic Line/Vector Rendering)              │
│  - JavaScript Event Listeners (Keydown / Keyup / Mouse)     │
└──────────────┬──────────────────────────────▲───────────────┘
               │ Event Coordinates            │ UI State
               ▼                              │
┌─────────────────────────────────────────────────────────────┐
│                     Python Backend Logic                    │
│  - Continuity Engine (Auto-Snapping coordinates)            │
│  - Passcode Sequence Orchestrator                           │
└──────────────┬──────────────────────────────────────────────┘
               │ Write on Save
               ▼
┌─────────────────────────────────────────────────────────────┐
│                     JSON Database Export                    │
│  - Structured play-by-play events                           │
│  - Ready for local momentum analysis                        │
└─────────────────────────────────────────────────────────────┘

```

* **Frontend Engine:** **NiceGUI** `ui.interactive_image` with an SVG overlay. NiceGUI is selected because it runs natively in Python but renders in a local browser window. It captures pixel-perfect mouse coordinates (`image_x`, `image_y`) dynamically regardless of window scaling.
* **Data Format:** A single local `match_session.json` file.

---

## 5. Event Data Schema (JSON Export Example)

A completed possession chain containing a pass and a tackle decomposes into a structured list of events:

```json
{
  "match_id": "eng-v-nzl-2026-07-15",
  "possession_chain_id": "chain_001",
  "events": [
    {
      "event_id": "evt_001",
      "timestamp_seconds": 122.5,
      "event_type": "PASS",
      "team": "ENG",
      "player_number": 9,
      "coords_start": {"x": 22.4, "y": 45.0},
      "coords_end": {"x": 35.1, "y": 42.2},
      "metadata": {
        "receiver_number": 10
      }
    },
    {
      "event_id": "evt_002",
      "timestamp_seconds": 124.1,
      "event_type": "CARRY",
      "team": "ENG",
      "player_number": 10,
      "coords_start": {"x": 35.1, "y": 42.2},
      "coords_end": {"x": 48.9, "y": 40.0},
      "metadata": {
        "meters_gained": 13.8
      }
    },
    {
      "event_id": "evt_003",
      "timestamp_seconds": 125.8,
      "event_type": "TACKLED_RUCK",
      "team": "NZL",
      "player_number": 7,
      "coords_start": {"x": 48.9, "y": 40.0},
      "coords_end": {"x": 48.9, "y": 40.0},
      "metadata": {
        "tackle_outcome": "ruck_formed",
        "phase_end": true
      }
    }
  ]
}

```

---

## 6. MVP Implementation Roadmap

### Milestone 1: NiceGUI Canvas Sandbox (Week 1)

* Set up a NiceGUI window displaying a standard rugby pitch image.
* Write JavaScript-to-Python event bridges to track mouse button drags and coordinate logging on click release.

### Milestone 2: Keyboard Held State & Continuity Snapping (Week 2)

* Develop the logic to check if a user is holding `W`, `E`, or `Q` during a click-and-drag.
* Implement the snapping rule ($\Delta t < 1000\text{ms}$) to stitch lines together.

### Milestone 3: Passcode Overlay & Storage (Week 3)

* Render absolute-positioned modal input fields over the vector endpoints on the pitch when a play ends.
* Implement automatic tab-focusing across the input sequence.
* Package annotated paths into the standard JSON schema and save locally.

---