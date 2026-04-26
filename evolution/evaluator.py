import math
from typing import Tuple
import neat
from config.settings import EnvironmentConfig, PhysicsConfig
from core import Body, Environment, update_sensors, check_eat

def brain_inputs(sens):
    return [sens["hunger"],sens["eye_left"],sens["eye_center"],sens["eye_right"],sens["smell"],sens["wall_left"],sens["wall_right"],sens["wall_front"],sens["memory"],sens.get("novelty",0.0),sens.get("stuck",0.0),sens.get("rand",0.0)]

def create_net(genome, config):
    if config.genome_config.feed_forward:
        return neat.nn.FeedForwardNetwork.create(genome, config)
    return neat.nn.RecurrentNetwork.create(genome, config)

def evaluate_genome(genome: neat.DefaultGenome, neat_config: neat.Config, env_config: EnvironmentConfig, physics_config: PhysicsConfig, max_steps: int = 2000) -> Tuple[float, int, int]:
    net = create_net(genome, neat_config)
    env = Environment(env_config); env.reset(initial_food=15)
    body = Body.random_placement(physics_config)
    fitness = 0.0; eaten = 0; steps = 0; dt = 1.0 / 20.0
    prev_x, prev_y, prev_z = body.x, body.y, body.z
    total_distance = 0.0; idle_steps = 0
    visited_cells = set()
    while steps < max_steps and body.energy > 0:
        update_sensors(body, env)
        output = net.activate(brain_inputs(body.get_sensors()))
        move_raw = output[0]
        cmd = {"forward": max(0.0, min(1.0, move_raw)) if move_raw > 0.2 else 0.0, "backward": max(0.0, min(1.0, -move_raw)) if move_raw < -0.2 else 0.0, "turbo": 1.0 if output[4] > 0.65 else 0.0, "yaw": output[1], "pitch": output[2] * 0.5, "roll": output[3] * 0.5}
        body.memory = max(-1.0, min(1.0, 0.95 * body.memory + 0.05 * output[5]))
        wall_hit = body.update(dt, cmd)
        if wall_hit: fitness -= 20.0
        if check_eat(body, env):
            eaten += 1
            fitness += 100.0
        dx,dy,dz = body.x-prev_x, body.y-prev_y, body.z-prev_z
        step_dist = math.sqrt(dx*dx+dy*dy+dz*dz); total_distance += step_dist
        prev_x,prev_y,prev_z = body.x,body.y,body.z
        idle_steps = idle_steps + 1 if step_dist < 0.2 else 0
        body.sensors["stuck"] = min(1.0, idle_steps / 80.0); body.sensors["novelty"] = min(1.0, step_dist / 8.0)
        if idle_steps > 30: fitness -= 2.0

        cell = (int(body.x // 50), int(body.y // 50), int(body.z // 50))
        if cell not in visited_cells:
            visited_cells.add(cell)
            fitness += 5.0

        steps += 1
        if len(env.food) < 10: env.spawn_food(1)
        fitness -= 0.005
    fitness += body.energy * 0.3 + total_distance * 0.1
    return max(0.0, fitness), eaten, steps
