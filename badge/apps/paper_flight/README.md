# Paper Flight

Paper Flight is a tilt-controlled paper airplane endless runner through an ever-changing skyway.

## Usage

Open **Paper Flight** from the badge menu and press SELECT to launch.
The camera follows your folded paper airplane from behind, slightly above
and to the right. Fly through the mint-edged openings; touching a wall folds
the plane and ends the run. The whole wingspan must fit through each opening.

Hold the badge **at a comfortable angle and keep it still as you press
SELECT to launch**. That pose sets neutral bank and pitch for the run;
there is no fixed 45-degree offset. Roll it left/right to bank in that
direction. From this resting angle, tilt up to climb and down to dive.
This applies to both upright and flipped launches.
Small movements around your launch pose are ignored
to reduce jitter. Returning to this angle levels the plane and stops
the climb or sideways drift; it does not return you to the middle.
Every launch or restart captures a fresh neutral pose. Pausing and resuming
keep the current calibration; it does not drift automatically while flying.

| Control | Action |
| --- | --- |
| Tilt left / right | Bank and move left / right |
| Tilt up / down | Climb / dive |
| Directional buttons | Alternate steering, including in the simulator |
| SELECT | Launch, pause, resume, or restart after a crash |
| BACK | Pause; from pause or a crash, return to the title |
| HOME | Return to the badge menu |

Openings are generated continuously with bounded changes in position.
Speed increases gradually, openings become tighter, and the distance and
number of cleared gates appear at the top. Your longest distance is saved
after a crash using `badgeware.State`; pauses do not advance the course.
The cream paper, mint edges, and navy sky use no external image assets
other than the menu icon.

## Requirements

GitHub Universe 2026 firmware and its onboard accelerometer are required for
tilt steering. No extra hardware, network, or secrets are needed.
Directional buttons remain available when the simulator has no motion input;
an all-zero IMU reading or missing launch calibration displays
`NO TILT - USE ARROWS`. If the IMU was unavailable at launch, restart with
SELECT once it is working to capture a neutral pose.
Before each launch, the app checks the firmware's actual screen rotation.
If the display is flipped 180 degrees, tilt-controlled up/down is reversed
for that run. The launch orientation and neutral pose stay fixed through
flight and pause/resume, so changing the screen rotation cannot unexpectedly
reverse steering mid-run. Restart to capture a different orientation.
Banking uses the launch display orientation; directional buttons retain
their firmware-defined logical directions.

## Verification

Host-side flight regression tests:

```powershell
python -m unittest discover -s tests -p test_paper_flight.py
python .github\skills\hyb26-skill\scripts\validate_app.py badge\apps\paper_flight
```

In the Badge Simulator, launch, steer through openings with the arrows,
pause/resume, crash, and restart. The simulator is not proof of IMU behavior.
On a physical badge, launch at several comfortable angles and verify neutral
flight, fresh calibration on restart, unchanged calibration on resume,
both bank directions, climb and
dive signs, inverted use, wall/wing collisions, pause/resume, HOME/re-open,
and best-distance persistence. After deployment, also confirm the paper
airplane icon appears in the badge menu.
