import math
from typing import Dict, Any

from config.settings import PhysicsConfig
from services import GLOBAL_ENTROPY


def _clamp(v: float, a: float, b: float) -> float:
    return max(a, min(b, float(v)))


class Body:
    def __init__(
        self,
        x: float,
        y: float,
        z: float,
        config: PhysicsConfig,
        yaw: float = 0.0,
        pitch: float = 0.0,
        roll: float = 0.0,
    ):
        self.x, self.y, self.z = x, y, z
        self.yaw, self.pitch, self.roll = yaw, pitch, roll

        self.max_energy = config.max_energy
        self.energy = self.max_energy

        self.speed = config.speed
        self.turbo_speed = config.turbo_speed
        self.turbo_cost = config.turbo_cost
        self.backward_cost = config.backward_cost

        self.yaw_speed = config.yaw_speed
        self.pitch_speed = config.pitch_speed
        self.roll_speed = config.roll_speed

        self.base_metabolism = config.base_metabolism
        self.move_cost = config.move_cost
        self.rotation_cost = config.rotation_cost

        self.wall_margin = config.wall_margin
        self.wall_penalty = config.wall_penalty

        self.memory = 0.0
        self.last_collision = "none"
        self.last_step_speed = 0.0

        self.sensors: Dict[str, float] = {
            "hunger": 0.0,
            "eye_left": 0.0,
            "eye_center": 0.0,
            "eye_right": 0.0,
            "smell": 0.0,
            "wall_left": 0.0,
            "wall_right": 0.0,
            "wall_front": 0.0,
            "food_dx": 0.0,
            "food_dy": 0.0,
            "food_dz": 0.0,
            "food_dist": 0.0,
            "floor_dist": 0.0,
            "ceiling_dist": 0.0,
            "algae_near": 0.0,
            "current_x": 0.0,
            "current_y": 0.0,
            "current_z": 0.0,
            "speed": 0.0,
            "memory": 0.0,
            "novelty": 0.0,
            "stuck": 0.0,
            "rand": 0.0,
        }

    def update(self, dt: float, cmd: Dict[str, float]) -> bool:
        forward = _clamp(cmd.get("forward", 0.0), 0.0, 1.0)
        backward = _clamp(cmd.get("backward", 0.0), 0.0, 1.0)
        turbo = _clamp(cmd.get("turbo", 0.0), 0.0, 1.0)

        yaw_cmd = _clamp(cmd.get("yaw", 0.0), -1.0, 1.0)
        pitch_cmd = _clamp(cmd.get("pitch", 0.0), -1.0, 1.0)
        roll_cmd = _clamp(cmd.get("roll", 0.0), -1.0, 1.0)

        self.yaw += yaw_cmd * self.yaw_speed * dt
        self.pitch = _clamp(
            self.pitch + pitch_cmd * self.pitch_speed * dt,
            -math.pi / 3,
            math.pi / 3,
        )
        self.roll += roll_cmd * self.roll_speed * dt

        movement_deadzone = 0.05

        if forward > movement_deadzone and forward >= backward:
            move_dir = 1.0
            move_strength = forward
        elif backward > movement_deadzone:
            move_dir = -1.0
            move_strength = backward
        else:
            move_dir = 0.0
            move_strength = 0.0

        speed = self.turbo_speed if turbo > 0.5 else self.speed

        cos_p = math.cos(self.pitch)
        dx = cos_p * math.sin(self.yaw)
        dy = math.sin(self.pitch)
        dz = cos_p * math.cos(self.yaw)

        if move_dir:
            displacement = move_dir * move_strength * speed * dt
            self.x += displacement * dx
            self.y += displacement * dy
            self.z += displacement * dz
            self.last_step_speed = displacement / dt if dt > 0 else 0.0
        else:
            self.last_step_speed = 0.0

        energy_cost = self.base_metabolism * dt

        if move_dir == 1.0:
            energy_cost += self.move_cost * move_strength * dt
            if turbo > 0.5:
                energy_cost += self.turbo_cost * dt
        elif move_dir == -1.0:
            energy_cost += self.backward_cost * move_strength * dt

        rotation = abs(yaw_cmd) + abs(pitch_cmd) + abs(roll_cmd)

        if rotation > 0:
            energy_cost += self.rotation_cost * rotation * dt

        self.energy = max(0.0, self.energy - energy_cost)

        self.sensors["hunger"] = min(1.0, 1.0 - self.energy / self.max_energy)
        self.memory = _clamp(
            0.92 * self.memory + 0.08 * self.sensors["hunger"],
            -1.0,
            1.0,
        )
        self.sensors["memory"] = self.memory

        return self.last_collision != "none"

    def get_sensors(self):
        return self.sensors.copy()

    def get_state(self) -> Dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "yaw": self.yaw,
            "pitch": self.pitch,
            "roll": self.roll,
            "energy": self.energy,
            "max_energy": self.max_energy,
            "last_collision": self.last_collision,
        }

    @classmethod
    def random_placement(cls, config: PhysicsConfig, env_width=800, env_height=600, env_depth=800):
        margin = 100.0
        return cls(
            GLOBAL_ENTROPY.uniform(margin, env_width - margin),
            GLOBAL_ENTROPY.uniform(margin, env_height - margin),
            GLOBAL_ENTROPY.uniform(margin, env_depth - margin),
            config,
            GLOBAL_ENTROPY.uniform(-math.pi, math.pi),
            GLOBAL_ENTROPY.uniform(-math.pi / 6, math.pi / 6),
            GLOBAL_ENTROPY.uniform(-math.pi / 8, math.pi / 8),
        )

    def feed(self, amount: float):
        self.energy = min(self.max_energy, self.energy + amount)