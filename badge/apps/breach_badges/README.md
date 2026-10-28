# Breach Badges

Breach Badges is a two-player Bluetooth duel with destructible walls, weapon drops, and tactical defenses.

## Play

Install this folder on both Universe 2026 badges with matching firmware and
open **Breach Badges**. Hold the badges back to back to select a nearby opponent
using the firmware's Bluetooth badge link. Check the displayed name and press
**Select on both badges** to confirm. No phone, Wi-Fi, internet, or secrets
are needed. Select in the unpaired lobby starts practice against a bot.

| Button | Action |
| --- | --- |
| Up / Down | Move along your edge; also choose your next dash direction |
| Hold Select | Fire the equipped weapon |
| Back | Consume the stored defense |
| Menu | Abandon the match and return to pairing |
| Home | Return to the badge launcher |

Your ship is always turquoise on the **left**; the rival is pink on the right.
The whole arena is mirrored on the second badge. Break bricks, catch capsules
travelling toward your edge, and shoot through the gaps. A missed capsule is
lost. Gold supply bricks are tougher; cracks show ordinary brick damage.

Each round starts with 5 HP and a three-second countdown, then lasts 90 seconds.
Higher HP wins at timeout. A tie removes the wall and all shields and starts
one-hit sudden death. Simultaneous defeats replay sudden death without scoring.
First to two round wins takes the best-of-three match. Both players press
Select at match end to rematch.

## Weapons and defenses

One temporary weapon replaces the previous weapon for ten seconds; its glyph,
name, and remaining seconds appear at bottom left. The basic blaster is unlimited.
Capsules use their weapon color, with gold reserved for rapid fire and rare
two-hit shields. Bottom right shows your single stored defense.

| Item | Glyph / color | Behavior |
| --- | --- | --- |
| Basic blaster | B / white | Reliable single shots |
| Rapid blaster | R / gold | Rapid small shots; weak against thick bricks |
| Drill shot | D / violet | Slow shot that damages up to four bricks in a line |
| Scatter shot | S / green | Short-range outer fan, full-range center pellet; low brick damage |
| Rocket | ! / red | Slow, marked by a warning; bursts across nearby bricks |
| Energy shield | O / cyan | Absorbs the next hit |
| Strong shield | O+ / gold | Rare drop; absorbs two hits |
| Dash | ^ / cyan | Fast vertical burst, no invulnerability; 0.8-second cooldown |
| Repair kit | + / cyan | Restores 1 HP, capped at 5 |

Defenses are consumed with Back, including dash; collect another to use it
again. A new capsule replaces the stored defense. Shields persist until hit,
replaced by another shield, or the round ends. Rockets do one ship hit, not
repeated splash damage. Ricochet, EMP, reflector, decoy, and barrier patch are
not part of this launch set.

## Link and recovery

The central badge alone runs physics, damage, drops, scoring, and timers.
Its peer sends sequenced input and defense presses; compact binary snapshots
(not screen images) are split to fit negotiated link capacity (at most 85 bytes,
minimum supported capacity 12 bytes) and applied only when complete.
Backpressured messages are retried with bounded buffering. Stale input/state packets are ignored. There is no client-side
damage prediction.

Missing traffic or acknowledged snapshots for 650 ms, or a disconnected link, pauses the match without
awarding a win. Bring the **same badges** back together to reconnect and resume
the retained host state. An unrelated opponent is rejected during recovery.
Menu abandons the match without counting it as a loss. Closing the app or
rebooting discards the in-memory match; there is no saved ranking.

## Validation and hardware requirements

Requires the Universe 2026 firmware with `badgeware.link`, `Proximity`, and
logical Up/Down/Select/Back/Menu buttons. Practice runs without a second badge.
The browser simulator's Bluetooth stub cannot verify multiplayer.

Run the host-side checks from the repository root:

```powershell
python -m unittest discover -s tests -p test_breach_badges.py
python .github\skills\hyb26-skill\scripts\validate_app.py badge\apps\breach_badges
python .github\scripts\validate_app_readmes.py badge/apps
```

Two-badge physical verification is still required: confirm opponent names and
mutual acceptance, mirrored controls in both orientations, all pickups and
defenses, best-of-three and rematch, radio interruption with no scoring while
paused, same-peer reconnection, and sustained frame rate with a full wall and
maximum shots. Link throughput and reconnect behavior depend on firmware.
The Badge Simulator canvas was unavailable in the build session; no canvas or
physical-hardware verification is claimed.
