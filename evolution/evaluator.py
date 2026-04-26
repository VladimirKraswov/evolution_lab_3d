import math
from typing import Tuple
import neat
from config.settings import EnvironmentConfig, PhysicsConfig
from core import Body, Environment, update_sensors, check_eat

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
        sens.get("energy", 0.0),
        sens.get("speed_sensor", 0.0),
        sens.get("algae_near", 0.0),
        sens.get("current_x", 0.0),
        sens.get("current_z", 0.0),
        0.0 # extra space if needed or just padding to match 24
    ]

def evaluate_genome(genome: neat.DefaultGenome, neat_config: neat.Config, env_config: EnvironmentConfig, physics_config: PhysicsConfig, max_steps: int = 1500) -> Tuple[float, int, int]:
    net = neat.nn.FeedForwardNetwork.create(genome, neat_config)
    env = Environment(env_config); env.reset(initial_food=15)
    body = Body.random_placement(physics_config, env_config.width, env_config.height, env_config.depth)
    fitness = 0.0; eaten = 0; steps = 0; last_spawn = 0; dt = 1.0 / 20.0
    prev_x, prev_y, prev_z = body.x, body.y, body.z
    total_distance = 0.0; idle_steps = 0; total_collisions = 0

    while steps < max_steps and body.energy > 0:
        update_sensors(body, env)

        # Calculate distance to nearest food before moving
        d_to_food_before = 1000.0
        if env.food:
            d_to_food_before = min(math.sqrt((f["x"]-body.x)**2 + (f["y"]-body.y)**2 + (f["z"]-body.z)**2) for f in env.food)

        output = net.activate(brain_inputs(body.get_sensors()))
        move_raw = output[0]
        cmd = {"forward": max(0.0, min(1.0, move_raw)) if move_raw > 0.2 else 0.0, "backward": max(0.0, min(1.0, -move_raw)) if move_raw < -0.2 else 0.0, "turbo": 1.0 if output[4] > 0.65 else 0.0, "yaw": output[1], "pitch": output[2] * 0.5, "roll": output[3] * 0.5}
        body.memory = max(-1.0, min(1.0, 0.95 * body.memory + 0.05 * output[5]))
        cur = env.current_at(body.x, body.y, body.z)
        body.update(dt, cmd, env_config.width, env_config.height, env_config.depth, current=cur)

        if body.last_collision != "none":
            total_collisions += 1
            fitness -= 2.0

        if check_eat(body, env):
            eaten += 1
            fitness += 100.0
        else:
            # Reward approaching food
            if env.food:
                d_to_food_after = min(math.sqrt((f["x"]-body.x)**2 + (f["y"]-body.y)**2 + (f["z"]-body.z)**2) for f in env.food)
                if d_to_food_after < d_to_food_before:
                    fitness += 0.5 * (d_to_food_before - d_to_food_after)
                else:
                    fitness -= 0.1

        dx,dy,dz = body.x-prev_x, body.y-prev_y, body.z-prev_z
        step_dist = math.sqrt(dx*dx+dy*dy+dz*dz); total_distance += step_dist
        prev_x,prev_y,prev_z = body.x,body.y,body.z

        idle_steps = idle_steps + 1 if step_dist < 0.2 else 0
        body.sensors["stuck"] = min(1.0, idle_steps / 80.0); body.sensors["novelty"] = min(1.0, step_dist / 8.0)

        if idle_steps > 30: fitness -= 1.0

        steps += 1
        if steps - last_spawn > 100 and len(env.food) < 15: env.spawn_food(1); last_spawn = steps

        # Small penalty for living to encourage efficient food finding
        fitness -= 0.01

    fitness += body.energy * 0.1 + total_distance * 0.02
    return max(0.0, fitness), eaten, steps
