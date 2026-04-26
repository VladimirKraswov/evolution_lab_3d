import math
from typing import Dict, Any
from config.settings import PhysicsConfig
from services import GLOBAL_ENTROPY

class Body:
    def __init__(self, x: float, y: float, z: float, config: PhysicsConfig, yaw: float = 0.0, pitch: float = 0.0, roll: float = 0.0):
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
        self.roll_speed = config.roll_speed          # <-- теперь своё поле
        self.base_metabolism = config.base_metabolism
        self.move_cost = config.move_cost
        self.rotation_cost = config.rotation_cost
        self.wall_margin = config.wall_margin
        self.wall_penalty = config.wall_penalty
        self.memory = 0.0
        self.last_collision = "none"
        self.last_speed = 0.0
        self.sensors: Dict[str, float] = {
            "hunger":0.0,
            "eye_left":0.0,
            "eye_center":0.0,
            "eye_right":0.0,
            "smell":0.0,
            "wall_left":0.0,
            "wall_right":0.0,
            "wall_front":0.0,
            "memory":0.0,
            "novelty":0.0,
            "stuck":0.0,
            "rand":0.0,
            "food_dx":0.0,
            "food_dy":0.0,
            "food_dz":0.0,
            "food_dist":0.0,
            "floor_dist":0.0,
            "ceiling_dist":0.0,
            "energy":1.0,
            "speed_sensor":0.0,
            "algae_near":0.0,
            "current_x":0.0,
            "current_z":0.0
        }

    def update(self, dt: float, cmd: Dict[str, float], env_w: float = 800, env_h: float = 600, env_d: float = 800, current: tuple = (0,0,0)):
        forward, backward, turbo = cmd.get("forward",0.0), cmd.get("backward",0.0), cmd.get("turbo",0.0)
        yaw_cmd, pitch_cmd, roll_cmd = cmd.get("yaw",0.0), cmd.get("pitch",0.0), cmd.get("roll",0.0)
        self.yaw += yaw_cmd * self.yaw_speed * dt
        self.pitch = max(-math.pi/3, min(math.pi/3, self.pitch + pitch_cmd * self.pitch_speed * dt))
        self.roll += roll_cmd * self.roll_speed * dt
        move_dir, move_strength = (1.0, forward) if forward > 0.5 else ((-1.0, backward) if backward > 0.5 else (0.0, 0.0))
        speed = self.turbo_speed if turbo > 0.5 else self.speed
        cos_p = math.cos(self.pitch)
        dx = cos_p * math.sin(self.yaw)
        dy = math.sin(self.pitch)
        dz = cos_p * math.cos(self.yaw)
        if move_dir:
            displacement = move_dir * move_strength * speed * dt
            new_x, new_y, new_z = self.x + displacement * dx, self.y + displacement * dy, self.z + displacement * dz
            self.last_speed = (move_dir * move_strength * speed) / self.turbo_speed
        else:
            new_x, new_y, new_z = self.x, self.y, self.z
            self.last_speed = 0.0

        # Apply water current
        new_x += current[0] * dt
        new_y += current[1] * dt
        new_z += current[2] * dt

        m = self.wall_margin
        self.last_collision = "none"
        if new_x < m:
            new_x = m; self.yaw = math.pi - self.yaw; self.last_collision = "wall_x"
        elif new_x > env_w - m:
            new_x = env_w - m; self.yaw = math.pi - self.yaw; self.last_collision = "wall_x"

        if new_y < m:
            new_y = m; self.pitch = abs(self.pitch); self.last_collision = "floor"
        elif new_y > env_h - m:
            new_y = env_h - m; self.pitch = -abs(self.pitch); self.last_collision = "wall_y"

        if new_z < m:
            new_z = m; self.yaw = -self.yaw; self.last_collision = "wall_z"
        elif new_z > env_d - m:
            new_z = env_d - m; self.yaw = -self.yaw; self.last_collision = "wall_z"

        if self.last_collision != "none":
            self.energy -= self.wall_penalty
        self.x, self.y, self.z = new_x, new_y, new_z
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
        self.memory = max(-1.0, min(1.0, 0.92 * self.memory + 0.08 * self.sensors["hunger"]))
        self.sensors["memory"] = self.memory

    def get_sensors(self): return self.sensors.copy()
    def get_state(self) -> Dict[str, Any]: return {"x":self.x,"y":self.y,"z":self.z,"yaw":self.yaw,"pitch":self.pitch,"roll":self.roll,"energy":self.energy,"max_energy":self.max_energy, "last_collision": self.last_collision}

    @classmethod
    def random_placement(cls, config: PhysicsConfig, env_w: float = 800, env_h: float = 600, env_d: float = 800):
        return cls(
            GLOBAL_ENTROPY.uniform(env_w * 0.1, env_w * 0.9),
            GLOBAL_ENTROPY.uniform(env_h * 0.1, env_h * 0.9),
            GLOBAL_ENTROPY.uniform(env_d * 0.1, env_d * 0.9),
            config,
            GLOBAL_ENTROPY.uniform(-math.pi, math.pi),
            GLOBAL_ENTROPY.uniform(-math.pi/6, math.pi/6),
            GLOBAL_ENTROPY.uniform(-math.pi/8, math.pi/8),
        )

    def feed(self, amount: float):
        self.energy = min(self.max_energy, self.energy + amount)