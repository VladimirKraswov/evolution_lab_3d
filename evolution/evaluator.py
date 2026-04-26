import math
from typing import Tuple

import neat

from config.settings import EnvironmentConfig, PhysicsConfig
from core import Body, Environment, update_sensors, check_eat, clamp_to_environment


def brain_inputs(sens):
    return [
        sens["hunger"],
        sens["eye_left"],
        sens["eye_center"],
        sens["eye_right"],
        sens["smell"],
        sens["wall_left"],
        sens["wall_right"],
        sens["wall_front"],
        sens["memory"],
        sens.get("novelty", 0.0),
        sens.get("stuck", 0.0),
        sens.get("rand", 0.0),
    ]


def create_net(genome, config):
    if config.genome_config.feed_forward:
        return neat.nn.FeedForwardNetwork.create(genome, config)

    return neat.nn.RecurrentNetwork.create(genome, config)


def _nearest_food_distance(body: Body, env: Environment) -> float:
    if not env.food:
        return float("inf")

    best = float("inf")

    for food in env.food:
        dx = food["x"] - body.x
        dy = food["y"] - body.y
        dz = food["z"] - body.z
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)

        if dist < best:
            best = dist

    return best


def evaluate_genome(
    genome: neat.DefaultGenome,
    neat_config: neat.Config,
    env_config: EnvironmentConfig,
    physics_config: PhysicsConfig,
    max_steps: int = 2600,
) -> Tuple[float, int, int]:
    net = create_net(genome, neat_config)

    env = Environment(env_config)
    env.reset(initial_food=35)

    body = Body.random_placement(physics_config)
    clamp_to_environment(body, env, physics_config)

    fitness = 0.0
    eaten = 0
    steps = 0
    dt = 1.0 / 20.0

    prev_x, prev_y, prev_z = body.x, body.y, body.z
    total_distance = 0.0
    idle_steps = 0
    visited_cells = set()

    prev_food_dist = _nearest_food_distance(body, env)

    while steps < max_steps and body.energy > 0:
        update_sensors(body, env)

        output = net.activate(brain_inputs(body.get_sensors()))
        move_raw = float(output[0])

        cmd = {
            "forward": max(0.0, min(1.0, move_raw)) if move_raw > 0.03 else 0.0,
            "backward": max(0.0, min(1.0, -move_raw)) if move_raw < -0.2 else 0.0,
            "turbo": 1.0 if len(output) > 4 and float(output[4]) > 0.72 else 0.0,
            "yaw": float(output[1]),
            "pitch": float(output[2]) * 0.45,
            "roll": float(output[3]) * 0.35,
        }

        body.memory = max(-1.0, min(1.0, 0.95 * body.memory + 0.05 * float(output[5])))

        wall_hit = body.update(dt, cmd)
        floor_hit = clamp_to_environment(body, env, physics_config)

        if wall_hit:
            fitness -= 22.0

        if floor_hit:
            fitness -= 6.0

        if check_eat(body, env):
            eaten += 1
            fitness += 180.0
            prev_food_dist = _nearest_food_distance(body, env)

        current_food_dist = _nearest_food_distance(body, env)

        if math.isfinite(prev_food_dist) and math.isfinite(current_food_dist):
            improvement = prev_food_dist - current_food_dist

            if improvement > 0:
                fitness += improvement * 0.45
            else:
                fitness += improvement * 0.04

            if current_food_dist < 180:
                fitness += 0.35

            if current_food_dist < 90:
                fitness += 0.75

        prev_food_dist = current_food_dist

        dx = body.x - prev_x
        dy = body.y - prev_y
        dz = body.z - prev_z

        step_dist = math.sqrt(dx * dx + dy * dy + dz * dz)
        total_distance += step_dist

        prev_x, prev_y, prev_z = body.x, body.y, body.z

        idle_steps = idle_steps + 1 if step_dist < 0.18 else 0

        body.sensors["stuck"] = min(1.0, idle_steps / 80.0)
        body.sensors["novelty"] = min(1.0, step_dist / 8.0)

        if step_dist > 0.2:
            fitness += 0.04

        if idle_steps > 35:
            fitness -= 2.5

        cell = (
            int(body.x // 50),
            int(body.y // 50),
            int(body.z // 50),
        )

        if cell not in visited_cells:
            visited_cells.add(cell)
            fitness += 3.5

        steps += 1

        if len(env.food) < 28:
            env.spawn_food(1)

        fitness -= 0.003

    fitness += body.energy * 0.22
    fitness += total_distance * 0.035
    fitness += eaten * 60.0

    return max(0.0, fitness), eaten, steps