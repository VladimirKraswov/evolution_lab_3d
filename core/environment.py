from typing import List, Dict, Any
from config.settings import EnvironmentConfig
from services import GLOBAL_ENTROPY

class Environment:
    def __init__(self, config: EnvironmentConfig):
        self.width, self.height, self.depth = config.width, config.height, config.depth
        self.food: List[Dict[str, float]] = []
        self.food_energy = config.food_energy
    def spawn_food(self, count: int = 1):
        for _ in range(count):
            self.food.append({"x":GLOBAL_ENTROPY.uniform(20,self.width-20),"y":GLOBAL_ENTROPY.uniform(20,self.height-20),"z":GLOBAL_ENTROPY.uniform(20,self.depth-20),"energy":self.food_energy})
    def remove_food(self, index: int):
        if 0 <= index < len(self.food): self.food.pop(index)
    def get_state(self) -> Dict[str, Any]: return {"width":self.width,"height":self.height,"depth":self.depth,"food":self.food.copy()}
    def reset(self, initial_food: int = 20): self.food.clear(); self.spawn_food(initial_food)
