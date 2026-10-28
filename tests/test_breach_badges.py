"""Deterministic rules, transport, and firmware-surface tests for Breach Badges."""

import importlib.util
import os
from pathlib import Path
import random
import struct
import sys
import types
import unittest
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1] / "badge" / "apps" / "breach_badges"
spec = importlib.util.spec_from_file_location("breach_arena", APP / "arena.py")
arena = importlib.util.module_from_spec(spec)
spec.loader.exec_module(arena)


class Rules(unittest.TestCase):
    def setUp(self):
        random.seed(41)
        self.game = arena.Arena()
        self.game.phase = arena.PLAY

    def advance(self, seconds, controls=(0, 0)):
        for _ in range(round(seconds * 100)):
            self.game.step(0.01, controls)

    def shot(self, kind, x=125, y=43, side=0):
        return [x, y, 100 if side == 0 else -100, 0, side, kind, 340, 4 if kind == arena.DRILL else 1]

    def test_round_defaults_and_supplies(self):
        self.assertEqual(len(self.game.bricks), 60)
        self.assertEqual(sum(bool(x) for x in self.game.supply), 10)
        self.assertEqual([p.hp for p in self.game.players], [5, 5])
        self.assertEqual(self.game.remaining, 90)

    def test_countdown_and_movement_are_time_based(self):
        self.game.phase = arena.COUNTDOWN
        self.advance(2)
        self.assertEqual(self.game.phase, arena.COUNTDOWN)
        self.advance(1.1)
        self.assertEqual(self.game.phase, arena.PLAY)
        self.game.players[0].y = 100
        self.advance(0.5, (arena.DOWN, 0))
        self.assertAlmostEqual(self.game.players[0].y, 152.5)

    def test_movement_bounds(self):
        self.advance(4, (arena.UP, arena.DOWN))
        self.assertEqual(self.game.players[0].y, arena.TOP + 10)
        self.assertEqual(self.game.players[1].y, arena.BOTTOM - 10)

    def test_frame_rate_independence(self):
        other = arena.Arena()
        other.phase = arena.PLAY
        for _ in range(60):
            self.game.step(1 / 60, (arena.DOWN, 0))
        for _ in range(30):
            other.step(1 / 30, (arena.DOWN, 0))
        self.assertAlmostEqual(self.game.players[0].y, other.players[0].y)
        self.assertAlmostEqual(self.game.remaining, other.remaining)

    def test_brick_damage_and_supply_direction(self):
        self.game.bricks[0], self.game.supply[0] = 2, arena.RAPID
        self.game.shots = [self.shot(arena.BASIC)]
        self.game.step(0.01, (0, 0))
        self.assertEqual(self.game.bricks[0], 0)
        self.assertEqual(self.game.drops[0][2:], [arena.RAPID, 0])
        before = self.game.drops[0][0]
        self.game.step(0.1, (0, 0))
        self.assertLess(self.game.drops[0][0], before)

    def test_rapid_weaker_and_faster(self):
        self.game.supply = [0] * 60
        self.game.shots = [self.shot(arena.RAPID)]
        self.game.step(0.01, (0, 0))
        self.assertEqual(self.game.bricks[0], 7)
        p = self.game.players[0]
        p.weapon, p.weapon_time = arena.RAPID, 10
        self.game.shoot(0)
        self.assertEqual(p.cooldown, 0.1)

    def test_drill_hits_each_brick_once_and_four_total(self):
        self.game.bricks = [8] * 60
        self.game.supply = [0] * 60
        self.game.shots = [self.shot(arena.DRILL, x=123)]
        self.advance(0.6)
        self.assertEqual(self.game.bricks[:6], [3, 3, 3, 3, 8, 8])
        self.assertFalse(self.game.shots)

    def test_scatter_fan_and_range(self):
        p = self.game.players[0]
        p.weapon, p.weapon_time = arena.SCATTER, 10
        self.game.shoot(0)
        self.assertEqual(len(self.game.shots), 3)
        self.assertLess(self.game.shots[0][3], 0)
        self.assertGreater(self.game.shots[2][3], 0)
        self.assertEqual([s[6] for s in self.game.shots], [170, 340, 170])

    def test_rocket_blast_damages_neighbors(self):
        self.game.supply = [0] * 60
        self.game.explode(142, 61, 0)
        self.assertGreater(sum(hp < 8 for hp in self.game.bricks), 3)
        self.assertEqual(len(self.game.effects), 1)

    def test_pickups_replace_loadout_and_misses_disappear(self):
        p = self.game.players[0]
        self.game.drops = [[24.1, p.y, arena.ROCKET, 0], [24.1, 40, arena.SHIELD, 0]]
        self.game.step(0.01, (0, 0))
        self.assertEqual(p.weapon, arena.ROCKET)
        self.assertGreater(p.weapon_time, 9.99)
        self.assertEqual(p.defense, 0)
        self.assertFalse(self.game.drops)
        self.game.drops = [[295.9, self.game.players[1].y, arena.REPAIR, 1]]
        self.game.step(0.01, (0, 0))
        self.assertEqual(self.game.players[1].defense, arena.REPAIR)

    def test_weapon_expires(self):
        p = self.game.players[0]
        p.weapon, p.weapon_time = arena.ROCKET, 0.03
        self.advance(0.05)
        self.assertEqual(p.weapon, arena.BASIC)

    def test_shields_absorb_and_repair_caps(self):
        p = self.game.players[1]
        p.defense = arena.STRONG_SHIELD
        self.game.activate(1)
        self.assertEqual(p.shield, 2)
        for _ in range(3):
            self.game.shots = [self.shot(arena.BASIC, x=295.9, y=p.y)]
            self.game.step(0.01, (0, 0))
        self.assertEqual((p.hp, p.shield), (4, 0))
        p.defense = arena.REPAIR
        self.game.activate(1)
        self.assertEqual(p.hp, 5)
        p.defense = arena.REPAIR
        self.game.activate(1)
        self.assertEqual(p.hp, 5)

    def test_dash_consumed_and_cooldown_without_invulnerability(self):
        p = self.game.players[1]
        p.defense = arena.DASH
        p.direction = 1
        self.game.activate(1)
        self.assertEqual(p.defense, 0)
        before = p.y
        self.game.step(0.1, (0, 0))
        self.assertGreater(p.y - before, 40)
        p.defense = arena.DASH
        self.game.activate(1)
        self.assertEqual(p.defense, arena.DASH)
        self.game.shots = [self.shot(arena.BASIC, x=295.9, y=p.y)]
        self.game.step(0.001, (0, 0))
        self.assertEqual(p.hp, 4)

    def test_timeout_and_best_of_three(self):
        self.game.players[1].hp = 4
        self.game.remaining = 0.01
        self.advance(0.02)
        self.assertEqual(self.game.phase, arena.ROUND_OVER)
        self.assertEqual(self.game.scores, [1, 0])
        self.advance(5.6)
        self.assertEqual(self.game.phase, arena.PLAY)
        self.game.finish_round(0)
        self.assertEqual(self.game.phase, arena.MATCH_OVER)
        self.game.new_match()
        self.assertEqual(self.game.scores, [0, 0])
        self.assertEqual(self.game.round_number, 1)

    def test_tied_timeout_and_one_hit_sudden_death(self):
        self.game.remaining = 0.01
        self.advance(0.02)
        self.assertTrue(self.game.sudden)
        self.assertFalse(any(self.game.bricks))
        self.game.shots = [self.shot(arena.BASIC, 295.9, self.game.players[1].y)]
        self.game.step(0.01, (0, 0))
        self.assertEqual(self.game.scores, [1, 0])

    def test_simultaneous_defeat_is_not_a_free_point(self):
        for p in self.game.players:
            p.hp = 0
        self.game.step(0.01, (0, 0))
        self.assertTrue(self.game.sudden)
        self.assertEqual(self.game.scores, [0, 0])

    def test_projectiles_and_drops_bounded(self):
        for _ in range(100):
            self.game.shoot(0)
        self.assertEqual(len(self.game.shots), 32)
        self.game.supply = [arena.RAPID] * 60
        for i in range(60):
            self.game.damage_brick(i, 100, 0)
        self.assertEqual(len(self.game.drops), 12)

    def test_seeded_soak_valid_snapshots(self):
        for frame in range(20000):
            self.game.step(1 / 60, (arena.FIRE | (arena.UP if frame % 200 < 100 else arena.DOWN),
                                    arena.FIRE | (arena.DOWN if frame % 300 < 150 else arena.UP)))
            if frame % 60 == 0:
                other = arena.Arena()
                other.restore(self.game.snapshot())
                self.assertEqual(other.snapshot(), self.game.snapshot())
            if self.game.phase == arena.MATCH_OVER:
                self.game.new_match()


class Protocol(unittest.TestCase):
    def test_snapshot_round_trip_all_fields(self):
        game = arena.Arena()
        game.players[0].weapon = arena.ROCKET
        game.players[0].weapon_time = 9.25
        game.players[0].defense = arena.STRONG_SHIELD
        game.shoot(0)
        game.drops = [[130.25, 50.5, arena.DASH, 1]]
        other = arena.Arena()
        other.restore(game.snapshot())
        self.assertEqual(other.snapshot(), game.snapshot())

    def test_chunks_reorder_duplicates_and_atomic_application(self):
        data = arena.Arena().snapshot()
        fragments = arena.packets(42, data)
        receiver = arena.Assembler()
        self.assertLessEqual(max(map(len, fragments)), 85)
        self.assertIsNone(receiver.feed(fragments[-1]))
        self.assertIsNone(receiver.feed(fragments[-1]))
        result = None
        for packet in fragments[:-1]:
            result = receiver.feed(packet)
        self.assertEqual(result, data)
        self.assertIsNone(receiver.feed(fragments[0]))

    def test_loss_then_next_snapshot_and_sequence_wrap(self):
        data = arena.Arena().snapshot()
        receiver = arena.Assembler()
        receiver.feed(arena.packets(65535, data)[0])
        result = None
        for packet in arena.packets(0, data):
            result = receiver.feed(packet)
        self.assertEqual(result, data)
        self.assertIsNone(receiver.feed(arena.packets(65535, data)[1]))

    def test_truncation_does_not_change_live_state(self):
        game = arena.Arena()
        before = game.snapshot()
        with self.assertRaises((ValueError, IndexError, struct.error)):
            game.restore(before[:-2])
        self.assertEqual(game.snapshot(), before)

    def test_malformed_fragment_rejected(self):
        with self.assertRaises(ValueError):
            arena.Assembler().feed(b"S\x00\x00\x00\xffx")

    def test_invalid_supply_projectile_and_drop_enums_are_atomic(self):
        game = arena.Arena()
        original = game.snapshot()
        bad = bytearray(original)
        bad[11 + 24 + 60] = 250
        with self.assertRaises(ValueError):
            game.restore(bad)
        self.assertEqual(game.snapshot(), original)
        for bad_shot in (
                [100, 100, 100, 0, 0, 250, 200, 1],
                [100, 100, 100, 0, 4, arena.BASIC, 200, 1]):
            source = arena.Arena()
            source.shots = [bad_shot]
            with self.assertRaises(ValueError):
                game.restore(source.snapshot())
            self.assertEqual(game.snapshot(), original)
        source = arena.Arena()
        source.drops = [[100, 100, 250, 0]]
        with self.assertRaises(ValueError):
            game.restore(source.snapshot())
        self.assertEqual(game.snapshot(), original)


class FakeLink:
    links = []

    def __init__(self, _game):
        self.central = len(self.links) % 2 == 0
        self.partner = types.SimpleNamespace(id="peer", name="Nearby badge")
        self.linked = False
        self.inbox = []
        self.sent = []
        self.other = None
        self.delivery = True
        self.mtu = 85
        self.reject = False
        self.drop_states = False
        self.budget = None
        self.used = 0
        self.links.append(self)

    def pump(self):
        self.used = 0

    def update(self):
        pass

    def receive(self):
        inbox, self.inbox = self.inbox, []
        return inbox

    def send(self, message):
        if self.reject or len(message) > self.mtu or (self.budget is not None and self.used >= self.budget):
            return False
        self.used += 1
        self.sent.append(message)
        if self.other and self.delivery and not (self.drop_states and message[:1] == b"S"):
            self.other.inbox.append(message)
        return True

    def capacity(self):
        return self.mtu

    def leave(self):
        self.linked = False

    def close(self):
        self.leave()


class FakeProximity:
    def __init__(self, _link):
        pass

    def update(self, _now):
        pass

    def syncing(self):
        return None

    def rest(self, *_args):
        pass


class Screen:
    width, height = 320, 240

    def __init__(self):
        self.commands = []

    def rectangle(self, x, y, w, h):
        if w < 0 or h < 0:
            raise ValueError("Negative rectangle")
        self.commands.append(("box", (x, y, w, h), self.pen))

    def text(self, label, x, y):
        self.commands.append(("text", (label, x, y), self.pen))

    def measure_text(self, label):
        return len(label) * 6, 8


def load_runtime():
    screen = Screen()
    pressed, held = set(), set()
    badge = types.SimpleNamespace(
        mode=lambda _mode: None, pressed=lambda button: button in pressed,
        held=lambda button: button in held, ticks_delta=16)
    firmware = types.ModuleType("badgeware")
    firmware.link = types.SimpleNamespace(Link=FakeLink, Proximity=FakeProximity)
    env = {
        "badge": badge, "screen": screen, "HIRES": 1, "VSYNC": 2,
        "font": types.SimpleNamespace(nope="nope"),
        "image": types.SimpleNamespace(EVEN_ODD=1, OFF=0),
        "color": types.SimpleNamespace(rgb=lambda *values: values),
        "run": lambda _update: None,
    }
    for button in ("UP", "DOWN", "LEFT", "RIGHT", "SELECT", "BACK", "MENU", "HOME"):
        env["BUTTON_" + button] = button
    with patch.dict(sys.modules, {"arena": arena, "badgeware": firmware}), patch.object(os, "chdir"):
        original_path = sys.path[:]
        try:
            exec(compile((APP / "__init__.py").read_text(), str(APP / "__init__.py"), "exec"), env)
        finally:
            sys.path[:] = original_path
    return env, pressed, held, screen


class Runtime(unittest.TestCase):
    def setUp(self):
        FakeLink.links = []
        self.host, self.hp, self.hh, self.hs = load_runtime()
        self.client, self.cp, self.ch, self.cs = load_runtime()
        self.a, self.b = self.host["game"], self.client["game"]
        self.a.link.other, self.b.link.other = self.b.link, self.a.link

    def frames(self, count=1):
        for _ in range(count):
            self.a.update(0.02)
            self.b.update(0.02)
            self.a.draw()
            self.b.draw()
            self.hp.clear()
            self.cp.clear()
            self.hs.commands.clear()
            self.cs.commands.clear()

    def connect(self):
        self.a.link.linked = self.b.link.linked = True
        self.frames(5)

    def start_match(self):
        self.connect()
        self.hp.add("SELECT")
        self.cp.add("SELECT")
        self.frames(200)
        self.assertEqual(self.a.mode, "game")
        self.assertEqual(self.b.mode, "game")
        self.assertFalse(self.a.paused)
        self.assertFalse(self.b.paused)

    def test_both_must_confirm(self):
        self.connect()
        self.hp.add("SELECT")
        self.frames(50)
        self.assertEqual(self.a.mode, "offer")
        self.cp.add("SELECT")
        self.frames(30)
        self.assertEqual(self.a.mode, "game")
        self.assertEqual(self.b.mode, "game")

    def test_client_input_moves_authoritative_rival(self):
        self.start_match()
        before = self.a.arena.players[1].y
        self.ch.add("DOWN")
        self.frames(15)
        self.assertGreater(self.a.arena.players[1].y, before + 15)
        self.assertEqual(self.b.side, 1)
        self.assertEqual(self.b.px(294, 14), 12)

    def test_defense_edge_is_not_replayed(self):
        self.start_match()
        player = self.a.arena.players[1]
        player.hp, player.defense = 2, arena.REPAIR
        self.cp.add("BACK")
        self.frames(12)
        self.assertEqual(player.hp, 3)
        player.defense = arena.REPAIR
        self.frames(12)
        self.assertEqual(player.hp, 3)

    def test_disconnect_freezes_state_and_reconnect_resumes(self):
        self.start_match()
        self.a.link.linked = self.b.link.linked = False
        remaining = self.a.arena.remaining
        self.frames(100)
        self.assertTrue(self.a.paused)
        self.assertTrue(self.b.paused)
        self.assertEqual(self.a.arena.remaining, remaining)
        self.a.link.linked = self.b.link.linked = True
        self.frames(60)
        self.assertFalse(self.a.paused)
        self.assertLess(self.a.arena.remaining, remaining)
        self.assertEqual(self.a.arena.scores, [0, 0])

    def test_one_way_state_loss_pauses_host_too(self):
        self.start_match()
        self.a.link.drop_states = True
        self.frames(100)
        self.assertTrue(self.a.paused)
        self.assertTrue(self.b.paused)
        remaining = self.a.arena.remaining
        self.frames(100)
        self.assertEqual(self.a.arena.remaining, remaining)
        self.a.link.drop_states = False
        self.frames(60)
        self.assertFalse(self.a.paused)
        self.assertFalse(self.b.paused)

    def test_small_capacity_and_backpressure_complete_snapshots(self):
        self.a.link.mtu = self.b.link.mtu = 20
        self.a.link.budget = self.b.link.budget = 2
        self.start_match()
        self.assertLessEqual(max(map(len, self.a.link.sent)), 20)
        self.a.link.reject = True
        self.frames(20)
        self.assertTrue(self.a.state_packets or self.a.outbox)
        self.assertLessEqual(len(self.a.state_packets), 128)
        self.a.link.reject = False
        self.frames(100)
        self.assertFalse(self.a.paused)
        self.assertFalse(self.b.paused)

    def test_capacity_too_small_is_reported_and_pauses(self):
        self.start_match()
        self.a.link.mtu = 8
        with patch("builtins.print") as output:
            self.frames(50)
        self.assertTrue(self.a.paused)
        self.assertIn("capacity", self.a.notice)
        output.assert_called()

    def test_rejecting_link_retains_acceptance(self):
        self.connect()
        self.a.link.reject = True
        self.hp.add("SELECT")
        self.cp.add("SELECT")
        self.frames(20)
        self.assertTrue(self.a.outbox)
        self.a.link.reject = False
        self.frames(80)
        self.assertEqual(self.b.mode, "game")

    def test_rematch_needs_both_and_resets_score(self):
        self.start_match()
        self.a.arena.finish_round(0)
        self.a.arena.finish_round(0)
        self.frames(10)
        self.hp.add("SELECT")
        self.frames(20)
        self.assertEqual(self.a.arena.phase, arena.MATCH_OVER)
        self.cp.add("SELECT")
        self.frames(30)
        self.assertEqual(self.a.arena.scores, [0, 0])
        self.assertEqual(self.a.arena.match, 2)
        self.assertEqual(self.b.arena.match, 2)

    def test_practice_and_all_render_states(self):
        self.hp.add("SELECT")
        self.hh.update(("SELECT", "DOWN"))
        self.frames(300)
        self.assertTrue(self.a.practice)
        self.assertEqual(self.a.mode, "game")
        self.assertLess(self.a.arena.remaining, 90)
        self.a.arena.shots = [[90, 90, 70, 0, 0, arena.ROCKET, 200, 1]]
        self.a.arena.drops = [[90, 120, arena.STRONG_SHIELD, 0]]
        self.a.arena.players[0].shield = 2
        for phase in (arena.COUNTDOWN, arena.PLAY, arena.ROUND_OVER, arena.MATCH_OVER):
            self.a.arena.phase = phase
            self.a.draw()
        self.hp.add("MENU")
        self.frames()
        self.assertEqual(self.a.mode, "lobby")

    def test_unrelated_peer_cannot_take_over_paused_match(self):
        self.start_match()
        self.a.link.linked = False
        self.frames(2)
        self.a.link.partner.id = "unrelated"
        self.a.link.linked = True
        self.frames(2)
        self.assertFalse(self.a.link.linked)
        self.assertEqual(self.a.mode, "game")
        self.assertTrue(self.a.paused)


if __name__ == "__main__":
    unittest.main()
