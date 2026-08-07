# Draft tracking issue — CueWeb / rest_gateway parity for layer `start_after`

Ready to file on AcademySoftwareFoundation/OpenCue once the layer start-after PR lands.

---

**Title:** [cueweb/rest_gateway] Surface layer `start_after` (deferred booking) outside CueGUI

**Body:**

The layer start-after gate (`layer.ts_start_after`, PR #TBD; design in
`design/layer-start-after-spec.md`) added deferred layer booking: an automatic
license-shortage backoff plus an operator-facing `SetStartAfter` RPC, with full
support in pycue and CueGUI. Two surfaces were deliberately deferred:

1. **CueWeb**
   - Read-only first: a "Start After" column on the layer table (blank when
     `start_after == 0`, sorted on the raw epoch) and a row treatment while
     `start_after` is in the future, with `start_after_reason` as the tooltip —
     matching CueGUI's `LayerMonitorTree` treatment.
   - Then set/clear parity: a dialog equivalent to CueGUI's *Set Start After…*
     (`cuegui/LayerDialog.py:LayerStartAfterDialog`) calling
     `LayerInterface.SetStartAfter`; `start_after=0` clears.
   - CueWeb already tracks CueGUI's frame-state display overrides
     (`app/frames/frame-columns.tsx` `frameStateDisplayOverride`), so it should
     not diverge on this either.

2. **rest_gateway**
   - Register `SetStartAfter` for `LayerInterface`. Note `LayerInterface`
     registration there is already incomplete; this can ride along with a
     broader completion pass.

Proto surface (already merged): `Layer.start_after` (26, epoch seconds, 0 = not
set), `Layer.start_after_reason` (27, free text),
`LayerSetStartAfterRequest{layer, start_after, username}`.
