"""Physics and procedural-stage regression tests; no badge hardware needed."""

import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

SOURCE = Path(__file__).resolve().parents[1] / "badge" / "apps" / "micro_mario" / "game.py"
SPEC = importlib.util.spec_from_file_location("micro_mario_game", SOURCE)
model = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(model)


def advance(game, seconds, **controls):
    for _ in range(round(seconds * 120)):
        game.update(model.STEP, **controls)


def playing(biome=0):
    game = model.Game(12345, biome)
    game.start()
    advance(game, .03)
    return game


class GenerationTests(unittest.TestCase):
    def test_seed_replays_and_changes_layout(self):
        a = model.Level(123, 0)
        b = model.Level(123, 0)
        c = model.Level(124, 0)
        self.assertEqual(a.tiles, b.tiles)
        self.assertEqual(a.coins, b.coins)
        self.assertNotEqual(a.tiles, c.tiles)

    def test_encounter_order_widths_and_biomes_are_varied(self):
        first_encounters = set()
        widths = set()
        for seed in range(50):
            layouts = []
            for biome in range(3):
                level = model.Level(seed, biome)
                self.assertEqual(len(level.sections), 10)
                self.assertEqual({section[2] for section in level.sections}, set(range(10)))
                first_encounters.add(level.sections[0][2])
                widths.update(section[1] for section in level.sections)
                layouts.append(tuple(bytes(row) for row in level.tiles))
                for start, width, _pattern in level.sections:
                    self.assertGreaterEqual(width, 12)
                    self.assertLessEqual(start + width, 180)
                for coin in level.coins:
                    self.assertFalse(level.solid(int(coin[0] // 16), int(coin[1] // 16)))
            self.assertEqual(len(set(layouts)), 3)
        self.assertEqual(first_encounters, set(range(10)))
        self.assertGreaterEqual(len(widths), 6)

    def test_hundreds_of_seeds_have_bounded_gaps_and_safe_zones(self):
        for biome in range(3):
            for seed in range(200):
                level = model.Level(seed, biome)
                gap = 0
                kinds = {enemy.kind for enemy in level.enemies}
                self.assertEqual(kinds, {"walker", "turtle", "flying", "plant"})
                for col in range(model.COLS):
                    gap = 0 if level.tiles[model.FLOOR][col] else gap + 1
                    self.assertLessEqual(gap, 0 if biome == 2 else 3)
                for col in list(range(0, 12)) + list(range(92, 104)) + list(range(180, 192)):
                    self.assertEqual(level.tiles[model.FLOOR][col], 1)
                    self.assertFalse(any(level.tiles[row][col] for row in range(3, model.FLOOR)))
                for row in range(model.ROWS):
                    for col, tile in enumerate(level.tiles[row]):
                        if tile == 3:
                            self.assertEqual(level.tiles[row + 1][col], 0)
                            self.assertEqual(level.tiles[row + 2][col], 0)

    def test_generated_terrain_is_traversable(self):
        # A terrain-only runner jumps at every gap/obstacle; this checks actual
        # physics over complete stages, not just a maximum gap-width proxy.
        for biome in range(3):
            for case in range(36):
                seed = case // 3
                game = model.Game(seed, biome)
                game.start()
                game.power = ("small", "big", "fire")[case % 3]
                game.resize_player()
                game.level.enemies = []
                for frame in range(120 * 60):
                    p = game.player
                    ahead = int((p.x + p.w + 10) // model.TILE)
                    feet = int((p.y + p.h + 2) // model.TILE)
                    obstacle = any(game.level.solid(ahead, row)
                                   for row in range(int(p.y // model.TILE), feet))
                    jump = biome != 2 and p.grounded and (
                        not game.level.solid(ahead, feet) or obstacle)
                    direction = 1
                    if (biome != 2 and not p.grounded and p.vy > 0
                            and not game.level.solid(ahead, model.FLOOR)
                            and game.level.solid(int(p.x // model.TILE), model.FLOOR)):
                        direction = 0
                    vertical = -1 if p.y > 112 else 1 if p.y < 100 else 0
                    game.update(model.STEP, direction, jump, True, True, vertical)
                    if game.status != "play":
                        break
                self.assertEqual(game.status, "clear", (biome, seed, game.power, p.x, p.y))


class PhysicsTests(unittest.TestCase):
    def test_fixed_step_matches_different_frame_rates(self):
        a, b = playing(), playing()
        for _ in range(30):
            a.update(1 / 30, direction=1)
        for _ in range(120):
            b.update(1 / 120, direction=1)
        self.assertAlmostEqual(a.player.x, b.player.x, places=4)
        self.assertAlmostEqual(a.player.y, b.player.y, places=4)

    def test_jump_release_changes_height_and_run_is_faster(self):
        held, released = playing(), playing()
        held.update(model.STEP, jump=True, jump_held=True)
        released.update(model.STEP, jump=True)
        advance(held, .3, jump_held=True)
        advance(released, .3)
        self.assertLess(held.player.y, released.player.y - 15)
        walk, run = playing(), playing()
        advance(walk, .5, direction=1)
        advance(run, .5, direction=1, running=True)
        self.assertGreater(run.player.x, walk.player.x + 10)

    def test_question_block_and_two_column_head_collision(self):
        game = playing()
        game.player.x = 63
        game.player.y = 90
        game.player.vy = -200
        game.level.tiles[4][3] = 3
        game.level.tiles[4][4] = 2
        game.level.move(game.player, .08, game.bump)
        self.assertEqual(game.level.tiles[4][3], 4)
        self.assertEqual(game.player.y, 80)
        self.assertFalse(game.player.grounded)
        self.assertEqual(game.coins, 1)
        self.assertEqual(len(game.pickups), 1)
        game.bump(3, 4)
        self.assertEqual(game.coins, 1)

    def test_water_stroke_and_dive(self):
        up, down = playing(2), playing(2)
        up.player.y = down.player.y = 120
        advance(up, .5, vertical=-1)
        advance(down, .5, vertical=1)
        self.assertLess(up.player.y, down.player.y)
        up.update(model.STEP, jump=True)
        self.assertLess(up.player.vy, -90)

    def test_coyote_time_and_buffered_landing(self):
        game = playing()
        game.player.grounded = False
        game.coyote = .05
        game.update(model.STEP, jump=True, jump_held=True)
        self.assertLess(game.player.vy, -200)
        game = playing()
        game.player.y -= 2
        game.player.grounded = False
        game.player.vy = 120
        game.update(model.STEP, jump=True, jump_held=True)
        advance(game, .03, jump_held=True)
        self.assertLess(game.player.vy, -200)

    def test_shield_pickup_and_brick_breaking(self):
        game = playing()
        pickup = model.Body(game.player.x, game.player.y, 10, 10, "shield")
        game.pickups.append(pickup)
        game.update(model.STEP)
        self.assertTrue(game.shield)
        self.assertFalse(pickup.alive)
        game.level.tiles[8][10] = 2
        game.bump(10, 8)
        self.assertEqual(game.level.tiles[8][10], 0)

    def test_water_contact_damages_instead_of_stomping(self):
        game = playing(2)
        enemy = model.Body(90, 160, 12, 16, "turtle")
        game.level.enemies = [enemy]
        game.player.x, game.player.y, game.player.vy = 90, 147, 100
        game.update(model.STEP)
        self.assertEqual(game.status, "dead")
        self.assertEqual(enemy.kind, "turtle")

    def test_shield_damage_and_fatal_pits(self):
        game = playing()
        game.shield = True
        game.hurt()
        self.assertFalse(game.shield)
        self.assertEqual(game.lives, 3)
        game.hurt()
        self.assertEqual(game.status, "play")
        game.hurt(True)
        self.assertEqual(game.status, "dead")
        self.assertEqual(game.lives, 2)

    def test_checkpoint_respawn_and_game_over(self):
        game = playing()
        game.checkpoint = True
        game.hurt(True)
        advance(game, 1.1)
        self.assertEqual(game.status, "play")
        self.assertEqual(game.player.x, game.level.checkpoint)
        self.assertGreater(game.invincible, 1)
        game.lives = 1
        game.hurt(True)
        advance(game, 1.1)
        self.assertEqual(game.status, "gameover")

    def test_stomp_wings_shell_kick_stop_and_shell_enemy_hit(self):
        game = playing()
        enemy = model.Body(90, 160, 12, 16, "flying")
        game.level.enemies = [enemy]
        p = game.player
        for expected in ("turtle", "shell"):
            p.x, p.y, p.vy = enemy.x, enemy.y - p.h, 100
            game.update(model.STEP)
            self.assertEqual(enemy.kind, expected)
        p.x, p.y, p.vy = enemy.x - p.w + 1, enemy.y, 0
        game.update(model.STEP)
        self.assertGreater(enemy.vx, 0)
        victim = model.Body(enemy.x + 4, enemy.y, 12, 12, "walker")
        game.level.enemies.append(victim)
        game.move_enemy(enemy, model.STEP)
        self.assertFalse(victim.alive)
        p.x, p.y, p.vy = enemy.x, enemy.y - p.h, 100
        game.update(model.STEP)
        self.assertEqual(enemy.vx, 0)

    def test_plant_contact_is_not_stompable(self):
        game = playing()
        enemy = model.Body(100, 178, 12, 0, "plant")
        game.level.enemies = [enemy]
        game.clock = 1.2
        game.move_enemy(enemy, model.STEP)
        game.player.x, game.player.y = enemy.x, enemy.y
        game.update(model.STEP)
        self.assertEqual(game.status, "dead")
        self.assertTrue(enemy.alive)

    def test_clear_cycles_all_biomes_and_scores_once(self):
        game = playing()
        for biome in (0, 1, 2, 0):
            self.assertEqual(game.biome, biome)
            game.player.x = game.level.goal
            game.update(model.STEP)
            self.assertEqual(game.status, "clear")
            score = game.score
            game.update(1)
            self.assertEqual(game.score, score)
            game.next_stage()

    def test_coins_grant_life_and_timer_is_fatal(self):
        game = playing()
        for _ in range(100):
            game.coin()
        self.assertEqual(game.lives, 4)
        self.assertEqual(game.score, 10000)
        game.time = .001
        game.update(model.STEP)
        self.assertEqual(game.status, "dead")


class DisplayTests(unittest.TestCase):
    def setUp(self):
        self.blits = []
        self.labels = []
        self.modes = []
        screen = SimpleNamespace(
            width=214, height=160,
            measure_text=lambda label: (len(label) * 6, 7),
            shape=Mock(),
            text=lambda label, x, y: self.labels.append((label, x, y)),
            blit=lambda sprite, bounds: self.blits.append(bounds),
        )
        sheet = SimpleNamespace(sprite=lambda col, row: (col, row))
        picture = SimpleNamespace(spritesheet=lambda cols, rows: sheet)
        class Images:
            OFF = EVEN_ODD = NEAREST = 0

            def __call__(self, width, height):
                self.requested_size = (width, height)
                return screen

            def load(self, path):
                return picture

        state = SimpleNamespace(load=Mock(), save=Mock())
        display = SimpleNamespace(width=320, height=240, blit=Mock())
        self.runtime = {
            "badge": SimpleNamespace(mode=self.modes.append, ticks=1),
            "screen": display,
            "font": SimpleNamespace(nope=0),
            "image": Images(),
            "color": SimpleNamespace(rgb=lambda *args: args),
            "shape": SimpleNamespace(rectangle=lambda *args: args),
            "rect": lambda *args: args,
            "VSYNC": 1,
            "HIRES": 2,
            "run": Mock(),
        }
        source = SOURCE.with_name("__init__.py")
        with patch.dict("sys.modules", {"game": model, "badgeware": SimpleNamespace(State=state)}):
            with patch("os.chdir"), patch("sys.path", []):
                exec(compile(source.read_text(), str(source), "exec"), self.runtime)

    def test_uses_150_percent_scale_and_keeps_all_overlays_on_screen(self):
        self.assertEqual(self.modes, [3])
        self.assertEqual(self.runtime["image"].requested_size, (214, 160))
        for status, paused in (("title", False), ("play", True),
                               ("clear", False), ("gameover", False)):
            self.runtime["game"].status = status
            self.runtime["paused"] = paused
            self.labels.clear()
            self.runtime["draw_overlay"]()
            self.assertTrue(self.labels)
            for label, x, y in self.labels:
                self.assertGreaterEqual(x, 0, label)
                self.assertLessEqual(x + len(label) * 6, 214, label)
                self.assertGreaterEqual(y, 0, label)
                self.assertLessEqual(y + 7, 160, label)

    def test_present_scales_tiles_to_exactly_24_physical_pixels(self):
        badge = self.runtime["badge"]
        badge.pressed = lambda button: False
        self.runtime.update({name: index for index, name in enumerate((
            "BUTTON_SELECT", "BUTTON_BACK", "BUTTON_RIGHT", "BUTTON_LEFT"))})
        self.runtime["update"]()
        self.runtime["display"].blit.assert_called_once_with(
            self.runtime["screen"], (0, 0, 321.0, 240.0), 0)
        self.assertEqual(16 * 321 / 214, 24)
        self.assertEqual(16 * 240 / 160, 24)

    def test_camera_keeps_player_visible_through_world_and_jumps(self):
        game = self.runtime["game"]
        game.invincible = 0
        for power in ("small", "big", "fire"):
            game.power = power
            game.resize_player()
            for x in (0, 800, game.level.goal, model.COLS * model.TILE - 10):
                for y in (30, 90, 150, 208 - game.player.h):
                    game.player.x, game.player.y = x, y
                    self.blits.clear()
                    self.runtime["draw_world"]()
                    left, top, width, height = self.blits[-1]
                    self.assertGreaterEqual(left, -3)
                    self.assertLess(left, 214)
                    self.assertGreaterEqual(top + (18 if game.player.h == 14 else 4), 22)
                    self.assertLess(top + height, 160)
                    self.assertEqual((width, height), (-16, 32))
                    self.assertEqual(self.runtime["world_y"], 0)


class PowerupTests(unittest.TestCase):
    def collect(self, game, kind):
        pickup = model.Body(game.player.x, game.player.y, 12, 12, kind)
        game.pickups.append(pickup)
        game.update(model.STEP)
        self.assertFalse(pickup.alive)
        return pickup

    def test_question_blocks_progress_mushroom_flower_shield_in_every_biome(self):
        for biome in range(3):
            game = playing(biome)
            for index, (kind, form) in enumerate((
                    ("mushroom", "big"), ("flower", "fire"), ("shield", "fire"))):
                col = 4 + index
                game.level.tiles[8][col] = 3
                game.bump(col, 8)
                self.assertEqual(game.pickups[-1].kind, kind)
                pickup = game.pickups[-1]
                pickup.x, pickup.y = game.player.x, game.player.y
                game.update(model.STEP)
                self.assertEqual(game.power, form)
                self.assertFalse(pickup.alive)
                self.assertEqual(game.level.tiles[8][col], 4)
                game.bump(col, 8)
                self.assertEqual(game.coins, index + 1)
            self.assertTrue(game.shield)

    def test_growth_preserves_feet_and_waits_for_headroom(self):
        game = playing()
        bottom = game.player.y + game.player.h
        game.level.tiles[11][3] = 2
        self.collect(game, "mushroom")
        self.assertEqual(game.power, "big")
        self.assertEqual(game.player.h, 14)
        self.assertEqual(game.player.y + game.player.h, bottom)
        self.assertFalse(any(game.level.cells(game.player)))
        game.player.x = 5 * model.TILE
        game.update(model.STEP)
        self.assertEqual(game.player.h, 26)
        self.assertEqual(game.player.y + game.player.h, bottom)
        self.assertFalse(any(game.level.cells(game.player)))

    def test_mushroom_moves_reverses_at_wall_and_is_removed_in_pit(self):
        game = playing()
        pickup = model.Body(100, 196, 12, 12, "mushroom")
        pickup.vx = 32
        game.pickups = [pickup]
        game.level.tiles[12][8] = 2
        advance(game, 1)
        self.assertLess(pickup.vx, 0)
        self.assertLess(pickup.x, 116)
        pickup.y = 270
        game.update(model.STEP)
        self.assertFalse(pickup.alive)
        self.assertEqual(game.pickups, [])

    def test_repeat_mushroom_does_not_remove_flower_and_big_breaks_bricks(self):
        game = playing()
        self.collect(game, "mushroom")
        self.assertEqual(game.player.h, 26)
        game.level.tiles[8][10] = 2
        game.bump(10, 8)
        self.assertEqual(game.level.tiles[8][10], 0)
        self.collect(game, "flower")
        self.collect(game, "mushroom")
        self.assertEqual(game.power, "fire")

    def test_damage_steps_down_and_fatal_death_resets_forms_and_shots(self):
        game = playing()
        self.collect(game, "flower")
        self.collect(game, "shield")
        for form, shield, height in (("fire", False, 26), ("big", False, 26),
                                    ("small", False, 14)):
            game.invincible = 0
            bottom = game.player.y + game.player.h
            game.hurt()
            self.assertEqual((game.power, game.shield, game.player.h), (form, shield, height))
            self.assertEqual(game.player.y + game.player.h, bottom)
            self.assertEqual(game.lives, 3)
            self.assertGreater(game.invincible, 0)
        self.collect(game, "flower")
        game.shoot()
        self.assertTrue(game.fireballs)
        game.hurt(True)
        self.assertEqual(game.fireballs, [])
        advance(game, 1.1)
        self.assertEqual((game.power, game.player.h, game.shield), ("small", 14, False))

    def test_form_carries_across_stage_with_correct_spawn_size(self):
        game = playing()
        self.collect(game, "flower")
        self.collect(game, "shield")
        game.player.x = game.level.goal
        game.update(model.STEP)
        self.assertEqual(game.status, "clear")
        game.next_stage()
        self.assertEqual((game.power, game.player.h, game.shield), ("fire", 26, True))
        self.assertEqual(game.player.y + game.player.h, model.FLOOR * model.TILE)
        self.assertEqual(game.fireballs, [])

    def test_b_press_is_buffered_between_steps_and_hold_only_runs(self):
        game = playing()
        self.collect(game, "flower")
        game.player.direction = 1
        game.update(model.STEP / 2, shoot=True)
        self.assertEqual(len(game.fireballs), 0)
        game.update(model.STEP / 2)
        self.assertEqual(len(game.fireballs), 1)
        advance(game, .5, direction=1, running=True)
        self.assertEqual(len(game.fireballs), 1)
        self.assertGreater(game.player.vx, 100)

    def test_cooldown_two_shot_limit_and_facing_in_all_biomes(self):
        for biome in range(3):
            game = playing(biome)
            game.update(model.STEP, shoot=True)
            self.assertEqual(game.fireballs, [])
            self.collect(game, "flower")
            game.update(model.STEP, direction=1, shoot=True)
            self.assertEqual(len(game.fireballs), 1)
            self.assertGreater(game.fireballs[0].vx, 0)
            game.update(model.STEP, shoot=True)
            self.assertEqual(len(game.fireballs), 1)
            advance(game, .26)
            game.update(model.STEP, direction=-1, shoot=True)
            self.assertEqual(len(game.fireballs), 2)
            self.assertLess(game.fireballs[-1].vx, 0)
            # Keep both shots alive to isolate the concurrent-shot limit.
            game.fire_cooldown = 0
            game.update(model.STEP, shoot=True)
            self.assertEqual(len(game.fireballs), 2)

    def test_shots_bounce_die_on_wall_ceiling_and_expire(self):
        for obstacle in ("floor", "wall", "ceiling", "lifetime"):
            game = playing()
            shot = model.Body(100, 200, 6, 6, "fireball")
            shot.vx, shot.vy, shot.phase = 190, 100, 1.8
            game.fireballs = [shot]
            if obstacle == "wall":
                shot.x, shot.y = 121, 190
                game.level.tiles[11][8] = 2
                game.level.tiles[12][8] = 2
            elif obstacle == "ceiling":
                shot.y, shot.vy = 81, -200
                game.level.tiles[4][6] = 2
            elif obstacle == "lifetime":
                shot.phase = .001
            for _ in range(6):
                game.move_fireballs(model.STEP)
            if obstacle == "floor":
                self.assertTrue(shot.alive)
                self.assertLess(shot.vy, 0)
            else:
                self.assertEqual(game.fireballs, [], obstacle)

    def test_shots_defeat_each_enemy_once_and_ignore_hidden_plants(self):
        for kind in ("walker", "turtle", "flying", "shell", "plant"):
            game = playing()
            enemy = model.Body(120, 150, 12, 16, kind)
            shot = model.Body(117, 153, 6, 6, "fireball")
            shot.vx, shot.phase = 190, 1.8
            game.level.enemies = [enemy]
            game.fireballs = [shot]
            game.move_fireballs(model.STEP)
            self.assertFalse(enemy.alive, kind)
            self.assertEqual(game.score, 200)
            self.assertEqual(game.fireballs, [])
            game.move_fireballs(model.STEP)
            self.assertEqual(game.score, 200)
        enemy.alive, enemy.h = True, 0
        shot.alive, shot.phase = True, 1.8
        game.fireballs = [shot]
        game.move_fireballs(model.STEP)
        self.assertTrue(enemy.alive)
        self.assertTrue(shot.alive)


if __name__ == "__main__":
    unittest.main()
