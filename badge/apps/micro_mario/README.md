# Micro Mario

Micro Mario is an original retro platformer with seeded surface, cavern, and underwater adventures.

## Controls

Open **Micro Mario** from the badge menu. On the title screen, use Left/Right
to choose the starting biome, A/SELECT to start, or B/BACK to roll a new seed.

| Control | Action |
| --- | --- |
| D-pad Left/Right | Move; combine with B to run |
| A / SELECT | Jump; hold for height, release for a short hop |
| A / SELECT underwater | Tap repeatedly to swim upward |
| D-pad Up/Down underwater | Swim upward / dive |
| B / BACK | Hold to run or swim faster; tap to shoot with flower power |
| MENU | Pause/resume and show controls |
| HOME | Return to the badge launcher |

The 2026 firmware exposes orientation-aware SELECT and BACK actions rather than
NES-style A/B constants. The round SELECT and BACK gamepad pads serve as A and B
here; the physical switches marked A/B on some cases are directional controls,
not independent NES buttons. No raw GPIO remapping is used, so rotating the badge
keeps the logical controls consistent. In the simulator, use the arrows with
Space/Enter (A/SELECT), or its gamepad controls (J = SELECT, K = BACK).

## Adventure

The game renders a 214x160 scene at 1.5x onto the physical 320x240 display,
cropping the extra rightmost pixel. Sprites, tiles, and text are 25% smaller
than the previous 2x view (a 16-pixel tile now occupies 24 physical pixels).
Nearest-neighbor scaling keeps the pixel art sharp. The camera follows in both
directions so jumps and underwater movement remain visible. Physics and
collision sizes are independent of the display scale. Surface bushes have
layered silhouettes, shaded leaf clusters, highlights, and parallax scrolling.

Each seed generates a reproducible 192-column stage. Stages cycle through surface,
cavern, and underwater biomes with fresh layouts. Reach the gold pennant, then
press A to continue. Left/Right on the title lets you try any biome immediately.
There is no final stage; each clear starts another generated stage.

Mushroom-like walkers patrol ledges. Walking turtles retreat into shells when
stomped; touch a resting shell to kick it, and stomp a moving shell to stop it.
Stomp winged turtles to remove their wings. Pipe plants emerge periodically and
cannot be stomped. Underwater, avoid all enemy contact rather than stomping.

Collect coins for points and an extra life every 100 coins. Hit a gold question
block from below for a coin and a powerup:

| Current form | Question-block reward |
| --- | --- |
| Small | A purple mushroom that moves along platforms and makes you grow |
| Big | A flower that grants an orange outfit and bouncing fireballs |
| Fire | A shield that absorbs an enemy hit before your form is downgraded |

Tap B/BACK to shoot in your facing direction, including underwater; holding B
still runs and does not auto-fire. Up to two fireballs can be active, with a
short firing cooldown. Shots bounce off floors, disappear on walls or after a
short lifetime, and defeat walkers, turtles, shells, and exposed pipe plants.
Mushrooms never remove flower power. Big and fire forms can break ordinary
bricks from below. Growth keeps your feet planted and waits for headroom under
low ceilings. Enemy damage removes a shield first, then downgrades fire to big
or big to small, with a brief grace period. Pits and the timer are always fatal.
Forms and shields carry into the next stage but reset after losing a life.

Three lives, a midpoint checkpoint, and a short respawn grace period make
long stages forgiving. Death keeps collected coins and stage changes; game over
offers a same-seed retry or a return to the title. Best score persists through
`badgeware.State`; individual runs are not saved.
The legacy `pocket_plumber` state key is retained so renaming the app preserves
existing best scores.

Stages shuffle ten encounter families without repeating a family within a
stage, vary their widths and positions, and remix them separately for each
biome. Expect staircase ridges, high bridges with stepping-stone approaches,
paired pipes of different heights, tiered platform gardens, broad terraces,
uneven stepping stones, two-level reward arcades, raised gap landings,
sheltered paths, and combined pipe/flying-enemy encounters. Upper coin routes
reward exploration while a traversable lower route remains available.
Caverns add hanging rock formations; underwater stages turn gaps into reefs
and add overhangs, mid-water coin trails, and a continuous swimming lane.
Question blocks keep enough space beneath them for the grown player.

Terrain retains bounded two/three-tile gaps and safe start, checkpoint, and
finish areas. The original hero artwork has outlined facial details, cap,
gloves, overalls and boots, with separate idle, three-step running, jumping,
and swimming poses. Grown and flower-powered forms have hand-drawn frames,
not a stretched small sprite.

Physics runs at a fixed 120 Hz with bounded
catch-up and frame-rate-independent input. Levels use compact tile rows, one
small world atlas, a dedicated hero atlas, and nearby-enemy activation to
limit badge memory/work.

All artwork is original. This is a retro platformer, not an NES emulator or a
reproduction of Nintendo's characters, levels, music, or graphics. No network,
credentials, audio, or extra hardware is required.

## Development and verification

From the repository root:

```powershell
python tools\build_micro_mario_assets.py
python -m unittest discover -s tests -p test_micro_mario.py
python .github\skills\hyb26-skill\scripts\validate_app.py badge\apps\micro_mario
```

Open the Badge Simulator canvas with app `micro_mario` and use its Deploy
button to install after previewing. The simulator does not prove hardware
performance or touch behavior. On a physical 2026 badge, check all three biomes,
simultaneous D-pad/A/B input, short/full jumps, swimming, shell interactions,
plants, mushroom growth/headroom, flower pickup and B firing while running,
fireball bounces/enemy hits, power downgrades, shield blocks, checkpoint respawn,
pause, stage clear, game over,
HOME/reopen, best-score persistence, and controls in both orientations. Confirm
that the launcher displays the custom icon after deployment.
