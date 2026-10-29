"""Host-side regression tests for Bird Flight Lab's deterministic SI model."""

import importlib.util
import math
from pathlib import Path
import unittest


MODEL_PATH = Path(__file__).resolve().parents[1] / "badge" / "apps" / "bird_flight_lab" / "flight.py"
SPEC = importlib.util.spec_from_file_location("bird_flight_model", MODEL_PATH)
model = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(model)


def simulate(choices=None, dt=1 / 30):
    flight = model.Flight(model.parameters(model.selections() if choices is None else choices))
    for _ in range(math.ceil(150 / dt)):
        flight.step(dt)
        if flight.phase == 5:
            return flight
    raise AssertionError("Flight did not reach a report within 150 simulated seconds")


class FlightModelTests(unittest.TestCase):
    def test_local_roster_has_a_dozen_distinct_named_birds(self):
        names = {bird[0] for bird in model.PRESETS}
        self.assertEqual(len(model.PRESETS), 12)
        self.assertEqual(names, {
            "Peregrine Falcon", "Common Loon", "Barn Swallow",
            "Ring-necked Pheasant", "Green Heron", "Bald Eagle",
            "Red-tailed Hawk", "Mallard", "Canada Goose",
            "Ruby-throated Hummingbird", "Belted Kingfisher",
            "Pileated Woodpecker",
        })
        self.assertEqual(model.LIMITS[0], len(model.PRESETS))
        sizes = {(bird[1], bird[2]) for bird in model.PRESETS}
        self.assertEqual(len(sizes), 12)
        self.assertEqual(model.parameters(model.selections())["name"], "Mallard")

    def test_each_preset_resets_traits_and_supplies_its_own_parameters(self):
        for index, (name, mass, span, wing, power) in enumerate(model.PRESETS):
            with self.subTest(preset=name):
                choices = model.selections(index)
                self.assertEqual(choices, [index, 2, 2, wing, power, 1, 0])
                self.assertTrue(all(0 <= value < limit for value, limit in zip(choices, model.LIMITS)))
                parameters = model.parameters(choices)
                self.assertEqual(parameters["name"], name)
                self.assertEqual(parameters["mass"], mass)
                self.assertEqual(parameters["span"], span)
                self.assertEqual(parameters["power"], model.POWER_LEVELS[power] * mass)
                choices[1] = 4
                self.assertEqual(model.selections(index)[1], 2)

    def test_presets_complete_all_five_phases_and_land(self):
        for index in range(len(model.PRESETS)):
            with self.subTest(preset=index):
                flight = simulate(model.selections(index))
                self.assertEqual(flight.visited, [0, 1, 2, 3, 4])
                self.assertEqual(flight.outcome, "Soft landing")
                self.assertEqual(flight.height, 0)
                self.assertGreater(flight.takeoff_distance, 0)
                self.assertLess(flight.takeoff_distance, 120)
                self.assertGreater(flight.peak_height, 10)

    def test_wing_loading_changes_stall_speed_by_lift_equation(self):
        choices = model.selections()
        original = model.parameters(choices)
        choices[1] = 4
        heavier = model.parameters(choices)
        self.assertAlmostEqual(heavier["stall"] / original["stall"], math.sqrt(2))
        choices[1] = 2
        choices[2] = 4
        longer = model.parameters(choices)
        self.assertAlmostEqual(longer["stall"] / original["stall"], 1 / 1.3)
        self.assertEqual(original["stall"], model.parameters(model.selections())["stall"])

    def test_wind_changes_ground_run_not_stall_speed(self):
        choices = model.selections()
        choices[5] = 0
        tailwind = simulate(choices)
        choices[5] = 3
        headwind = simulate(choices)
        self.assertEqual(tailwind.config["stall"], headwind.config["stall"])
        self.assertLess(headwind.takeoff_distance, tailwind.takeoff_distance)

    def test_power_improves_takeoff(self):
        choices = model.selections()
        choices[4] = 1
        weaker = simulate(choices)
        choices[4] = 4
        stronger = simulate(choices)
        self.assertLess(stronger.takeoff_distance, weaker.takeoff_distance)

    def test_unflyable_configuration_reports_failed_takeoff(self):
        choices = model.selections()
        choices[1:5] = [4, 0, 2, 0]
        flight = simulate(choices)
        self.assertEqual(flight.outcome, "Cannot take off")
        self.assertEqual(flight.visited, [0])
        self.assertEqual(flight.height, 0)
        self.assertTrue(flight.reason)

    def test_thermal_can_turn_sinking_into_climbing(self):
        calm = simulate()
        choices = model.selections()
        choices[6] = 2
        rising_air = simulate(choices)
        self.assertLess(calm.soar_change, 0)
        self.assertGreater(rising_air.soar_change, 0)
        self.assertGreater(rising_air.peak_height, calm.peak_height)
        self.assertEqual(rising_air.outcome, "Soft landing")

    def test_soar_and_dive_use_no_muscle_energy(self):
        flight = model.Flight(model.parameters(model.selections()))
        while flight.phase < 2:
            flight.step(0.02)
        for phase in (2, 3):
            self.assertEqual(flight.phase, phase)
            energy = flight.energy
            start_speed = flight.speed
            while flight.phase == phase:
                flight.step(0.02)
            self.assertEqual(flight.energy, energy)
            if phase == 3:
                self.assertGreater(flight.speed, start_speed)

    def test_exhaustion_triggers_landing_and_stall_is_visible(self):
        flight = model.Flight(model.parameters(model.selections()))
        while flight.phase < 1:
            flight.step(0.02)
        flight.height = 20
        flight.energy = 0
        flight.step(0.02)
        self.assertEqual(flight.phase, 4)
        self.assertEqual(flight.energy, 0)
        flight.speed = flight.config["stall"] * 0.5
        flight.step(0.02)
        self.assertTrue(flight.stalled)
        self.assertLess(flight.lift_ratio, 1)

    def test_frames_and_fast_playback_produce_consistent_metrics(self):
        slow = simulate(dt=1 / 120)
        fast = simulate(dt=0.25)
        for attribute in ("takeoff_distance", "peak_speed", "peak_height", "soar_change", "time"):
            self.assertAlmostEqual(getattr(slow, attribute), getattr(fast, attribute), delta=0.15)
        self.assertEqual(slow.outcome, fast.outcome)

    def test_all_individual_settings_remain_finite_and_terminate(self):
        for preset in range(len(model.PRESETS)):
            for row, limit in enumerate(model.LIMITS):
                for value in range(limit):
                    with self.subTest(preset=preset, row=row, value=value):
                        choices = model.selections(preset)
                        choices[row] = value
                        flight = simulate(choices, dt=0.1)
                        for attribute in ("speed", "height", "energy", "distance", "peak_height"):
                            self.assertTrue(math.isfinite(getattr(flight, attribute)))
                        self.assertGreaterEqual(flight.height, 0)
                        self.assertGreaterEqual(flight.energy, 0)
                        self.assertLessEqual(flight.energy, 1)
                        self.assertTrue(flight.outcome)

    def test_finished_flight_does_not_change(self):
        flight = simulate()
        previous = dict(flight.__dict__)
        flight.step(30)
        self.assertEqual(flight.__dict__, previous)


if __name__ == "__main__":
    unittest.main()
