# Light Cycles

An original neon trail battle for the Universe 2026 Badger 2350 running MonaOS.

## Play

Open **Light Cycles** in the launcher. Use **Up/Down** to select **CPU Battle**
or **Nearby Badge**, then **Select** to play. Use the **d-pad** to steer;
direct 180-degree reversals are ignored. Every rider leaves a solid trail.
Hitting a wall, your own trail, or another rider's trail eliminates you.
Riders hitting the same cell simultaneously are both eliminated.

The last rider standing earns a point; simultaneous final crashes are a draw.
The first rider to five points wins the match. **Select** starts the next
round or a new match. Scores last only for the current session.

**Back** returns to the mode menu; **Home** returns to the launcher.

## CPU Battle

Battle two CPU riders. You are cyan; the bots are magenta and amber.
If you crash first, watch the surviving bots finish the round.

## Nearby Badge

Install this same app on both badges and choose **Nearby Badge** on each.
Hold the badges back to back to pair, then **both press Select** to accept.
The pairing screen identifies your color: cyan or magenta.
Both screens show the same arena, so directions are absolute, not mirrored.
Keep the badges nearby during play. Both players must press **Select** again
for each new round or match.

Dropped steps are retried; poor reception can slow play rather than split
the arenas. A lost connection returns to the pairing screen. Pull the badges
apart before pairing again. No Wi-Fi credentials or shared settings change.

## Requirements

Requires Universe 2026 firmware with the runtime graphics API and
`badgeware.link` Link/Proximity support. CPU Battle needs one badge; Nearby
Badge needs two badges running the same app. No Wi-Fi credentials or other
configuration are required. The app uses the 320x240 HIRES display mode.

Copy this directory to `/system/apps/light_cycles/` using USB mass-storage
mode, safely eject **BADGER**, and restart the badge. No launcher modifications
are required to play. `icon.png` is original artwork for the menu tile.

## Verification

Rules, CPU behavior, controls, score flow, and two-peer messaging were exercised
off-badge, including packet loss, duplication, reordering, and reconnects.
The app also ran in the browser's MicroPython simulator. Real-badge controls,
performance, and pairing/radio play still need testing on two physical badges.
