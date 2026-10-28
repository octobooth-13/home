"""Host-side regression tests for Paper Flight's tilt and swept collisions."""

import ast
import importlib.util
import math
from pathlib import Path
import random
import unittest
from unittest.mock import Mock


SOURCE = Path(__file__).resolve().parents[1] / "badge" / "apps" / "paper_flight" / "flight.py"
SPEC = importlib.util.spec_from_file_location("paper_flight_logic", SOURCE)
flight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(flight)


class TiltTests(unittest.TestCase):
    def axes(self, ax, ay, az, inverted=False):
        return flight.tilt_axes(ax, ay, az, (0, math.pi / 4), inverted)

    def test_45_degree_hold_is_neutral_at_any_scale(self):
        for scale in (1, 1000, 16384):
            self.assertEqual(self.axes(0, scale, -scale), (0, 0))

    def test_deadzone_and_missing_imu(self):
        self.assertEqual(self.axes(300, 16384, -16084), (0, 0))
        self.assertIsNone(self.axes(0, 0, 0))

    def test_bank_and_pitch_signs(self):
        self.assertGreater(self.axes(8000, 14000, 0)[0], 0)
        self.assertLess(self.axes(-8000, 14000, 0)[0], 0)
        for degrees, direction in ((30, -1), (60, 1)):
            angle = math.radians(degrees)
            pitch = self.axes(0, math.cos(angle) * 16384,
                                     -math.sin(angle) * 16384)[1]
            self.assertGreater(pitch * direction, 0)

    def test_upright_pose_commands_dive_from_tilted_reference(self):
        self.assertEqual(self.axes(0, 16384, 0), (0, -1))

    def test_bank_sensitivity_does_not_increase_with_pitch(self):
        for degrees in (0, 30, 45, 60):
            angle = math.radians(degrees)
            bank = self.axes(4000, 15000 * math.cos(angle),
                                    -15000 * math.sin(angle))[0]
            self.assertAlmostEqual(bank, self.axes(4000, 15000, 0)[0])

    def test_inversion_matches_logical_orientation(self):
        normal = self.axes(4000, 15000, -6000)
        inverted = self.axes(-4000, -15000, -6000, True)
        self.assertEqual(normal[0], inverted[0])
        self.assertEqual(normal[1], -inverted[1])
        for scale in (1, 1000, 16384):
            self.assertEqual(self.axes(0, -scale, -scale, True), (0, 0))

    def test_flipped_pitch_and_resting_offset_both_reverse(self):
        for degrees in (0, 30, 45, 60, 90):
            angle = math.radians(degrees)
            ay = math.cos(angle) * 16384
            az = -math.sin(angle) * 16384
            normal = self.axes(0, ay, az)[1]
            flipped = self.axes(0, -ay, az, True)[1]
            self.assertAlmostEqual(flipped, -normal)

    def test_flipped_neutral_does_not_drift(self):
        game = flight.Flight(random.Random(7))
        for _ in range(60):
            game.advance(1 / 60, *self.axes(0, -16384, -16384, True))
        self.assertEqual((game.x, game.y, game.pitch), (0, 0, 0))

    def test_scale_independent_and_saturated(self):
        self.assertEqual(self.axes(1, 2, -1), self.axes(1000, 2000, -1000))
        self.assertEqual(self.axes(16384, 0, -16384), (1, 1))

    def test_launch_pose_is_neutral_at_any_angle_and_orientation(self):
        for inverted in (False, True):
            for degrees in (-60, -30, 0, 20, 45, 70, 90):
                angle = math.radians(degrees)
                for ax in (-3000, 0, 3000):
                    ay = math.cos(angle) * 15000 * (-1 if inverted else 1)
                    az = -math.sin(angle) * 15000
                    reference = flight.tilt_angles(ax, ay, az, inverted)
                    self.assertEqual(flight.tilt_axes(ax, ay, az, reference, inverted),
                                     (0, 0))

    def test_calibration_changes_neutral_without_changing_gain(self):
        first = flight.tilt_angles(0, 16384, 0)
        second = flight.tilt_angles(0, 16384, -16384)
        self.assertGreater(flight.tilt_axes(0, 16384, -16384, first)[1], 0)
        self.assertEqual(flight.tilt_axes(0, 16384, -16384, second), (0, 0))
        self.assertLess(flight.tilt_axes(0, 16384, 0, second)[1], 0)

    def test_no_reading_or_calibration_is_explicitly_unavailable(self):
        self.assertIsNone(flight.tilt_angles(0, 0, 0))
        self.assertIsNone(flight.tilt_axes(0, 16384, 0, None))
        self.assertIsNone(flight.tilt_axes(0, 0, 0, (0, 0)))


class LaunchOrientationTests(unittest.TestCase):
    def setUp(self):
        source = SOURCE.with_name("__init__.py")
        tree = ast.parse(source.read_text())
        functions = [node for node in tree.body
                     if isinstance(node, ast.FunctionDef)
                     and node.name in ("start", "controls")]
        self.badge = Mock()
        self.badge.rotate_180.return_value = False
        self.badge.imu.return_value = (0, 15000, -5000, 0, 0, 0)
        self.badge.held.return_value = False
        self.ns = dict(badge=self.badge, flight=flight.Flight(random.Random(7)),
                       tilt_angles=flight.tilt_angles, tilt_axes=flight.tilt_axes,
                       BUTTON_RIGHT="right", BUTTON_LEFT="left",
                       BUTTON_UP="up", BUTTON_DOWN="down")
        exec(compile(ast.Module(body=functions, type_ignores=[]),
                     str(source), "exec"), self.ns)

    def test_launch_captures_flipped_state_and_reverses_pitch(self):
        for inverted, direction in ((False, 1), (True, -1)):
            self.badge.rotate_180.return_value = inverted
            self.badge.imu.return_value = (0, 15000, -5000, 0, 0, 0)
            self.ns["start"]()
            self.assertEqual(self.ns["launch_inverted"], inverted)
            self.assertEqual(self.ns["controls"](), (0, 0))
            self.badge.imu.return_value = (0, 15000, -10000, 0, 0, 0)
            self.assertGreater(self.ns["controls"]()[1] * direction, 0)

    def test_rotation_changes_do_not_change_run_controls(self):
        self.ns["start"]()
        self.badge.imu.return_value = (0, 15000, -10000, 0, 0, 0)
        before = self.ns["controls"]()
        self.badge.rotate_180.return_value = True
        self.assertEqual(self.ns["controls"](), before)
        self.ns["start"]()
        self.assertTrue(self.ns["launch_inverted"])
        self.assertEqual(self.ns["controls"](), (0, 0))

    def test_logical_up_button_is_not_inverted_again(self):
        self.badge.rotate_180.return_value = True
        self.ns["start"]()
        self.badge.held.side_effect = lambda button: button == "up"
        self.assertEqual(self.ns["controls"](), (0, 1))


class FlightTests(unittest.TestCase):
    def game(self, gate=None):
        game = flight.Flight(random.Random(7))
        if gate is not None:
            game.gates = [gate]
        return game

    def test_level_flight_does_not_drift(self):
        game = self.game()
        game.advance(0.1, 0, 0)
        self.assertEqual((game.x, game.y), (0, 0))
        self.assertAlmostEqual(game.distance, 1.6, places=3)

    def test_wings_must_fit_not_just_plane_center(self):
        game = self.game([0, 0, 1.4, 3.3, 2.6])
        game.x = 2.3
        game.advance(0.1, 0, 0)
        self.assertFalse(game.alive)
        self.assertEqual(game.passed, 0)

    def test_pitch_clearance_and_nose_collision(self):
        game = self.game([0, 0, 1.4, 3.3, 2.6])
        game.y = -2.4
        game.advance(0.1, 0, 0)
        self.assertFalse(game.alive)

    def test_banked_wing_clearance_matches_drawn_vertices(self):
        game = self.game([0, 0, 1.4, 3.3, 2.6])
        game.bank = 1
        game.y = 2.1
        self.assertGreater(max(p[1] for p in game.vertices()) + game.y, 2.6)
        game.advance(0.1, 1, 0)
        self.assertFalse(game.alive)

    def test_score_only_after_tail_clears_whole_wall(self):
        game = self.game([0, 0, 0, 3.3, 2.6])
        game.advance(0.1, 0, 0)
        self.assertTrue(game.alive)
        self.assertEqual(game.passed, 0)
        game.advance(0.1, 0, 0)
        self.assertEqual(game.passed, 1)
        game.advance(0.1, 0, 0)
        self.assertEqual(game.passed, 1)

    def test_tail_can_still_collide_after_nose_passes(self):
        game = self.game([0, 0, -0.5, 3.3, 2.6])
        game.x = 2.3
        game.advance(0.1, 0, 0)
        self.assertFalse(game.alive)

    def test_high_speed_cannot_tunnel_through_wall(self):
        game = self.game([0, 0, 1.4, 3.3, 2.6])
        game.distance = 100000
        game.x = 5
        game.advance(0.1, 0, 0)
        self.assertFalse(game.alive)

    def test_time_step_independence(self):
        outcomes = []
        for fps in (30, 60, 120):
            game = self.game()
            game.gates = [[0, 0, 1000, 3.3, 2.6]]
            for _ in range(fps):
                game.advance(1 / fps, 0.6, -0.4)
            outcomes.append((game.x, game.y, game.distance, game.bank))
        for outcome in outcomes[1:]:
            for actual, expected in zip(outcome, outcomes[0]):
                self.assertAlmostEqual(actual, expected, places=6)

    def test_generated_course_is_bounded_and_reachable(self):
        game = self.game()
        old_x = old_y = 0
        for index in range(1000):
            game.distance = index * 100
            x, y, z, width, height = game.make_gate(100)
            self.assertLessEqual(abs(x), 6)
            self.assertLessEqual(abs(y), 3)
            if index:
                self.assertLessEqual(abs(x - old_x), 3.2 + 1e-8)
                self.assertLessEqual(abs(y - old_y), 2 + 1e-8)
            self.assertGreaterEqual(width, 2.6 - 1e-8)
            self.assertGreaterEqual(height, 2.1 - 1e-8)
            old_x, old_y = x, y

    def test_endless_recycling_is_bounded_and_spaced(self):
        game = self.game()
        for _ in range(4000):
            # Follow the route exactly to exercise recycling, not steering skill.
            game.x, game.y = game.gates[0][:2]
            game.advance(0.1, 0, 0)
            self.assertTrue(game.alive)
            self.assertEqual(len(game.gates), 5)
            for a, b in zip(game.gates, game.gates[1:]):
                self.assertAlmostEqual(b[2] - a[2], game.SPACING)
        self.assertGreater(game.passed, 100)

    def test_generated_course_can_be_steered_at_maximum_difficulty(self):
        game = self.game()
        for _ in range(60 * 180):
            target = next(gate for gate in game.gates
                          if gate[2] >= game.TAIL - game.THICKNESS)
            game.advance(1 / 60, (target[0] - game.x) * 1.5,
                         (target[1] - game.y) * 1.5)
            self.assertTrue(game.alive)
        self.assertGreater(game.distance, 4000)
        self.assertGreater(game.passed, 150)

    def test_reset_restores_run_and_dead_flight_freezes(self):
        game = self.game()
        game.alive = False
        game.advance(0.1, 1, 1)
        self.assertEqual(game.distance, 0)
        game.reset()
        self.assertTrue(game.alive)
        self.assertEqual((game.x, game.y, game.passed), (0, 0, 0))
        self.assertEqual(len(game.gates), 5)

    def test_long_frames_and_invalid_controls_are_bounded(self):
        game = self.game()
        game.advance(10, 100, -100)
        self.assertLess(game.distance, 4)
        self.assertTrue(-1 <= game.bank <= 1)
        self.assertTrue(-1 <= game.pitch <= 1)
        before = game.distance
        game.advance(-1, 0, 0)
        self.assertEqual(game.distance, before)


if __name__ == "__main__":
    unittest.main()
