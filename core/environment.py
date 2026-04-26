from typing import List, Dict, Any
import math
import time
from typing import List, Dict, Any
from config.settings import EnvironmentConfig
from services import GLOBAL_ENTROPY

class Environment:
    def __init__(self, config: EnvironmentConfig):
        self.width, self.height, self.depth = config.width, config.height, config.depth
        self.food: List[Dict[str, Any]] = []
        self.food_energy = config.food_energy
        self.start_time = time.time()

    def spawn_food(self, count: int = 1):
        for _ in range(count):
            food_type = "small"
            energy = self.food_energy
            if GLOBAL_ENTROPY.random() < 0.15:
                food_type = "rich"
                energy = self.food_energy * 2.5

            self.food.append({
                "x": GLOBAL_ENTROPY.uniform(20, self.width-20),
                "y": GLOBAL_ENTROPY.uniform(20, self.height-20),
                "z": GLOBAL_ENTROPY.uniform(20, self.depth-20),
                "energy": energy,
                "type": food_type
            })

    def remove_food(self, index: int):
        if 0 <= index < len(self.food): self.food.pop(index)

    def current_at(self, x: float, y: float, z: float):
        # Deterministic procedural current
        t = (time.time() - self.start_time) * 0.5
        cx = math.sin(z * 0.01 + t) * 5.0
        cz = math.cos(x * 0.01 + t) * 5.0
        return cx, 0.0, cz

    def get_state(self) -> Dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "depth": self.depth,
            "food": self.food.copy(),
            "current_seed": self.start_time
        }

    def reset(self, initial_food: int = 20):
        self.food.clear()
        self.spawn_food(initial_food)
