from dataclasses import dataclass, field


@dataclass
class EnvironmentConfig:
    width: int = 800
    height: int = 600
    depth: int = 800
    initial_food_count: int = 20
    food_energy: float = 50.0


@dataclass
class PhysicsConfig:
    max_energy: float = 200.0
    base_metabolism: float = 1.5
    move_cost: float = 3.0
    rotation_cost: float = 1.5
    speed: float = 100.0
    turbo_speed: float = 160.0
    turbo_cost: float = 6.0
    backward_cost: float = 4.0
    yaw_speed: float = 1.8
    pitch_speed: float = 1.0
    roll_speed: float = 1.0
    wall_margin: float = 10.0
    wall_penalty: float = 8.0


@dataclass
class BrainConfig:
    input_size: int = 12
    output_size: int = 6


@dataclass
class AppConfig:
    env: EnvironmentConfig = field(default_factory=EnvironmentConfig)
    physics: PhysicsConfig = field(default_factory=PhysicsConfig)
    brain: BrainConfig = field(default_factory=BrainConfig)

    host: str = "0.0.0.0"
    port: int = 3030

    # Физика чаще, чем WebSocket. Это и даёт плавный realtime.
    sim_hz: int = 90
    broadcast_hz: int = 30

    # Старое поле оставлено для совместимости с UI.
    fps: int = 30


CONFIG = AppConfig()