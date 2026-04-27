import math
import random
from typing import List, Dict, Any

from config.settings import EnvironmentConfig
from services import GLOBAL_ENTROPY


class Environment:
    def __init__(self, config: EnvironmentConfig):
        self.width = config.width
        self.height = config.height
        self.depth = config.depth

        self.food: List[Dict[str, float]] = []
        self.food_energy = config.food_energy

        self.terrain_grid = 32
        self.terrain_texture = "/data/textures/sand.png"
        self._hills = self._make_hills()
        self.terrain = self._build_terrain_mesh()
        self.algae = self._generate_algae()

    def _make_hills(self):
        rng = random.Random(9127)
        hills = []

        for _ in range(10):
            hills.append({
                "cx": rng.uniform(self.width * 0.08, self.width * 0.92),
                "cz": rng.uniform(self.depth * 0.08, self.depth * 0.92),
                "rx": rng.uniform(75, 190),
                "rz": rng.uniform(75, 190),
                "h": rng.uniform(10, 44),
            })

        return hills

    def floor_height_at(self, x: float, z: float) -> float:
        nx = max(0.0, min(1.0, x / max(1.0, self.width)))
        nz = max(0.0, min(1.0, z / max(1.0, self.depth)))

        h = 8.0
        h += math.sin(nx * math.pi * 2.4 + 0.6) * math.cos(nz * math.pi * 1.8) * 8.0
        h += math.sin((nx * 4.2 + nz * 2.7) * math.pi) * 5.0
        h += math.sin((nx - nz) * math.pi * 5.0) * 3.5

        for hill in self._hills:
            dx = (x - hill["cx"]) / hill["rx"]
            dz = (z - hill["cz"]) / hill["rz"]
            h += hill["h"] * math.exp(-(dx * dx + dz * dz) * 0.5)

        return max(3.0, min(86.0, h))

    def _build_terrain_mesh(self) -> Dict[str, Any]:
        vertices = []
        cells = []
        grid = self.terrain_grid

        for iz in range(grid + 1):
            z = self.depth * iz / grid

            for ix in range(grid + 1):
                x = self.width * ix / grid
                y = self.floor_height_at(x, z)

                vertices.append({
                    "x": x,
                    "y": y,
                    "z": z,
                    "u": x / 96.0,
                    "v": z / 96.0,
                })

        for iz in range(grid):
            for ix in range(grid):
                a = iz * (grid + 1) + ix
                b = a + 1
                d = (iz + 1) * (grid + 1) + ix
                c = d + 1

                cells.append({
                    "a": a,
                    "b": b,
                    "c": c,
                    "d": d,
                })

        return {
            "type": "sand_mesh",
            "grid": grid,
            "texture": self.terrain_texture,
            "vertices": vertices,
            "cells": cells,
        }

    def _generate_algae(self):
        rng = random.Random(4312)
        algae = []

        count = 70

        for _ in range(count):
            x = rng.uniform(28, self.width - 28)
            z = rng.uniform(28, self.depth - 28)
            y = self.floor_height_at(x, z)

            algae.append({
                "x": x,
                "y": y,
                "z": z,
                "height": rng.uniform(28, 72),
                "width": rng.uniform(2.8, 5.8),
                "lean": rng.uniform(-0.22, 0.22),
                "phase": rng.uniform(0.0, math.pi * 2.0),
                "stiffness": rng.uniform(0.75, 1.35),
                "segments": rng.randint(5, 7),
                "spread": rng.uniform(7.0, 13.0),
                "color_shift": rng.uniform(-0.18, 0.18),
            })

        return algae

    def current_at(self, x: float, y: float, z: float, time: float) -> tuple:
        # Procedural, deterministic current
        # Use simple sine waves
        cx = math.sin(x * 0.005 + time * 0.5) * 5.0
        cz = math.cos(z * 0.005 + time * 0.5) * 5.0
        cy = math.sin(y * 0.01 + time * 0.3) * 2.0
        return cx, cy, cz

    def spawn_food(self, count: int = 1):
        for _ in range(count):
            x = GLOBAL_ENTROPY.uniform(20, self.width - 20)
            z = GLOBAL_ENTROPY.uniform(20, self.depth - 20)

            floor_y = self.floor_height_at(x, z)
            min_y = floor_y + 35
            max_y = self.height - 25

            if min_y >= max_y:
                y = self.height * 0.5
            else:
                y = GLOBAL_ENTROPY.uniform(min_y, max_y)

            # Different food types
            ftype = "small"
            energy = self.food_energy
            if GLOBAL_ENTROPY.random() < 0.15:
                ftype = "rich"
                energy = self.food_energy * 2.5

            self.food.append({
                "x": x,
                "y": y,
                "z": z,
                "energy": energy,
                "type": ftype,
                "drift_seed": GLOBAL_ENTROPY.random() * 100.0
            })

    def remove_food(self, index: int):
        if 0 <= index < len(self.food):
            self.food.pop(index)

    def get_state(self) -> Dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "depth": self.depth,
            "food": [item.copy() for item in self.food],
            "terrain": self.terrain,
            "algae": [item.copy() for item in self.algae],
        }

    def reset(self, initial_food: int = 20):
        self.food.clear()
        self.spawn_food(initial_food)