import math
from typing import Tuple

import neat

from config.settings import EnvironmentConfig, PhysicsConfig
from core import Body, Environment, update_sensors, check_eat, clamp_to_environment


def brain_inputs(sens):
    return [
        sens.get("hunger", 0.0),
        sens.get("eye_left", 0.0),
        sens.get("eye_center", 0.0),
        sens.get("eye_right", 0.0),
        sens.get("smell", 0.0),
        sens.get("wall_left", 0.0),
        sens.get("wall_right", 0.0),
        sens.get("wall_front", 0.0),
        sens.get("memory", 0.0),
        sens.get("novelty", 0.0),
        sens.get("stuck", 0.0),
        sens.get("rand", 0.0),
        sens.get("food_dx", 0.0),
        sens.get("food_dy", 0.0),
        sens.get("food_dz", 0.0),
        sens.get("food_dist", 0.0),
        sens.get("floor_dist", 0.0),
        sens.get("ceiling_dist", 0.0),
        sens.get("algae_near", 0.0),
        sens.get("speed", 0.0),
        sens.get("current_x", 0.0),
        sens.get("current_y", 0.0),
        sens.get("current_z", 0.0),
        sens.get("energy_status", 0.0), # Will add to update_sensors
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

    body = Body.random_placement(
        physics_config,
        env_width=env.width,
        env_height=env.height,
        env_depth=env.depth,
    )
    clamp_to_environment(body, env, physics_config)

    fitness = 0.0
    metrics = {
        "eaten": 0,
        "steps": 0,
        "collisions": 0,
        "stuck_steps": 0,
        "total_distance": 0.0,
        "approach_reward": 0.0,
    }

    dt = 1.0 / 20.0
    prev_x, prev_y, prev_z = body.x, body.y, body.z
    idle_steps = 0
    visited_cells = set()
    prev_food_dist = _nearest_food_distance(body, env)

    # Track spinning
    recent_yaws = []
    env.time = 0.0

    while metrics["steps"] < max_steps and body.energy > 0:
        env.time += dt

        # Update drifting food
        for food in env.food:
            seed = food.get("drift_seed", 0.0)
            food["x"] += math.sin(env.time * 0.4 + seed) * 0.15
            food["z"] += math.cos(env.time * 0.3 + seed) * 0.15

        update_sensors(body, env)

        output = net.activate(brain_inputs(body.get_sensors()))
        move_raw = float(output[0])
        yaw_val = float(output[1])

        cmd = {
            "forward": max(0.0, min(1.0, move_raw)) if move_raw > 0.03 else 0.0,
            "backward": max(0.0, min(1.0, -move_raw)) if move_raw < -0.2 else 0.0,
            "turbo": 1.0 if len(output) > 4 and float(output[4]) > 0.72 else 0.0,
            "yaw": yaw_val,
            "pitch": float(output[2]) * 0.45,
            "roll": float(output[3]) * 0.35,
        }

        body.memory = max(-1.0, min(1.0, 0.95 * body.memory + 0.05 * float(output[5])))

        before_x, before_y, before_z = body.x, body.y, body.z
        body.update(dt, cmd)

        # Apply current and algae drag in evaluation too
        cx, cy, cz = env.current_at(body.x, body.y, body.z, env.time)
        body.x += cx * 0.2 * dt
        body.y += cy * 0.2 * dt
        body.z += cz * 0.2 * dt

        algae_factor = body.sensors.get("algae_near", 0.0)
        if algae_factor > 0.1:
            drag = 1.0 - algae_factor * 0.4
            body.x = before_x + (body.x - before_x) * drag
            body.y = before_y + (body.y - before_y) * drag
            body.z = before_z + (body.z - before_z) * drag

        hit = clamp_to_environment(body, env, physics_config)

        dx = body.x - before_x
        dy = body.y - before_y
        dz = body.z - before_z
        step_dist = math.sqrt(dx*dx + dy*dy + dz*dz)
        body.last_step_speed = step_dist / dt
        body.sensors["energy_status"] = body.energy / body.max_energy

        metrics["total_distance"] += step_dist

        if hit:
            metrics["collisions"] += 1
            if body.last_collision == "floor":
                fitness -= 10.0
            else:
                fitness -= 30.0

        if check_eat(body, env):
            metrics["eaten"] += 1
            fitness += 250.0
            prev_food_dist = _nearest_food_distance(body, env)

        current_food_dist = _nearest_food_distance(body, env)
        if math.isfinite(prev_food_dist) and math.isfinite(current_food_dist):
            improvement = prev_food_dist - current_food_dist
            if improvement > 0:
                reward = improvement * 0.6
                fitness += reward
                metrics["approach_reward"] += reward
            else:
                fitness += improvement * 0.1

            # Proximity reward
            if current_food_dist < 100:
                fitness += 1.0
            elif current_food_dist < 200:
                fitness += 0.4

        prev_food_dist = current_food_dist

        # Stuck detection
        if step_dist < 0.2:
            idle_steps += 1
            if idle_steps > 20:
                fitness -= 1.0
                metrics["stuck_steps"] += 1
        else:
            idle_steps = 0
            fitness += 0.05 # Movement reward

        # Penalty for excessive spinning
        recent_yaws.append(yaw_val)
        if len(recent_yaws) > 100:
            recent_yaws.pop(0)
            avg_yaw = sum(recent_yaws) / len(recent_yaws)
            if abs(avg_yaw) > 0.8:
                fitness -= 0.5

        # Exploration bonus
        cell = (int(body.x // 60), int(body.y // 60), int(body.z // 60))
        if cell not in visited_cells:
            visited_cells.add(cell)
            fitness += 4.0

        metrics["steps"] += 1

        # Increase food spawns as generations progress?
        # Actually curriculum usually means making it harder.

        if len(env.food) < 30:
            env.spawn_food(1)

        fitness -= 0.01 # Time penalty

    # Final rewards/penalties
    fitness += metrics["eaten"] * 100.0
    fitness += body.energy * 0.2

    if metrics["eaten"] == 0:
        fitness *= 0.5 # Severe penalty for not eating anything

    return max(0.0, fitness), metrics["eaten"], metrics["steps"]