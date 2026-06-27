# Spike — Closed-loop auto-pause for the Kobra X

**Status:** research / not proven on the Kobra X. Default `AUTO_PAUSE_ENABLED=false`.
**Goal:** when PrintGuard reports a *sustained* failure, actually **pause/cancel** the Kobra X — not
just alert.

## The core problem

The Kobra X is camera-only for our detection (closed K4 firmware, no Rinkhals/OctoPrint/Moonraker).
PrintGuard's built-in auto-pause only works through an OctoPrint/Klipper/Bambu connection, which the X
doesn't expose. So pausing needs a **separate control channel** to the printer.

## Three candidate routes (ranked)

### 1. Anycubic **Cloud** MQTT — MOST VIABLE ✅ (but unverified on X)
- The official app talks to the printer via **Anycubic cloud MQTT (port 8883)** using your account.
- `WaresWichall/hass-anycubic_cloud` (Home Assistant) already does **pause / resume / cancel** on
  sibling K4 printers via this cloud path — **no rooting** required.
- `metheos/anycubic-s1-mqtt-bridge` is the reference for the **message schema** (proven on the
  Kobra S1, the X's closest sibling).
- **Unknowns to confirm on the Kobra X specifically:**
  - Does the X share the S1's cloud command topic/schema? (likely, same K4 era — confirm.)
  - Auth flow: account login → device list → printer_id → command publish.
  - Latency: cloud round-trip is seconds, fine for "sustained failure" pausing.
- **Risk:** cloud-dependent (needs internet + Anycubic staying up); unofficial (could break on a
  firmware update).

### 2. Fully-**local** MQTT (port 18086, mTLS) — BLOCKED today ⛔
- The printer runs a local MQTT broker on `127.0.0.1:18086` with **mutual-TLS**. To talk to it you
  need the device's certs, which on other models are extracted via the **Rinkhals** root overlay.
- **Rinkhals does not support the Kobra X** yet → no supported way to pull certs. Park this; revisit
  if/when Rinkhals adds the X.

### 3. Smart-plug kill switch — LAST RESORT ⚠️
- Cut mains power on sustained failure. Stops wasted filament but: abrupt power loss can leave a
  blob/mess, is hard on the hardware, and loses the print bed heat profile. Only consider if 1 & 2
  both fail and filament waste is the dominant cost.

## Recommended spike plan

1. **Account + device discovery.** Stand up `hass-anycubic_cloud` (or just its auth module) against
   the real account; confirm the Kobra X appears and capture its `printer_id`.
2. **Read-only first.** Subscribe to the cloud status topic; confirm we can *see* the X's state
   (printing/paused/progress). Zero risk.
3. **Command test on a throwaway print.** Publish a `pause` command; confirm the X pauses. Then
   `resume`. Capture the exact topic + payload that worked.
4. **Wire the adapter.** Fill in `service/app/pause.py:try_cloud_pause()` with the proven publish.
   Keep it behind `AUTO_PAUSE_ENABLED` + a **confirmation cooldown** (don't pause on a single frame —
   require PrintGuard's sustained-detection count, which we already get from the webhook).
5. **Safety.** Always alert Discord *and* pause; log a `pause` event to `print_events`. Never auto-
   **cancel** (destructive) on detection — pause + human decision only.

## Decision gate

Ship auto-pause **only** if step 3 reproducibly pauses the X. Otherwise document "not feasible on X
today" with the captured evidence and stay alert-only. Alert-only is already a complete, useful product.

## Sources
- https://github.com/WaresWichall/hass-anycubic_cloud
- https://github.com/metheos/anycubic-s1-mqtt-bridge
- https://wiki.anycubic.com/en/fdm-3d-printer/anycubic-kobra-x/lan-connection-guide
- https://github.com/jbatonnet/Rinkhals  (Kobra X unsupported as of 2026-03)
