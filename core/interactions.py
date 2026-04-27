import math

from .body import Body, _clamp
from .environment import Environment
from services import GLOBAL_ENTROPY


def update_sensors(body: Body, env: Environment):
    for key in [
        "eye_left",
        "eye_center",
        "eye_right",
        "smell",
        "wall_left",
        "wall_right",
        "wall_front",
        "food_dx",
        "food_dy",
        "food_dz",
        "food_dist",
        "floor_dist",
        "ceiling_dist",
        "algae_near",
        "current_x",
        "current_y",
        "current_z",
        "speed",
    ]:
        body.sensors[key] = 0.0

    smell_range = 420.0
    vision_range = 480.0

    if env.food:
        nearest_dist_sq = float("inf")
        nearest_food = None

        for food in env.food:
            dx = food["x"] - body.x
            dy = food["y"] - body.y
            dz = food["z"] - body.z
            dist_sq = dx * dx + dy * dy + dz * dz

            if dist_sq < nearest_dist_sq:
                nearest_dist_sq = dist_sq
                nearest_food = food

        if nearest_food is not None and nearest_dist_sq > 0:
            dx = nearest_food["x"] - body.x
            dy = nearest_food["y"] - body.y
            dz = nearest_food["z"] - body.z
            dist = math.sqrt(nearest_dist_sq)

            # Local coordinates
            cos_y = math.cos(body.yaw)
            sin_y = math.sin(body.yaw)
            # Yaw rotation (around Y)
            lx = dx * cos_y - dz * sin_y
            lz = dx * sin_y + dz * cos_y
            # Pitch rotation (around X) - simplified for sensors
            ly = dy

            body.sensors["food_dx"] = _clamp(lx / 500.0, -1.0, 1.0)
            body.sensors["food_dy"] = _clamp(ly / 500.0, -1.0, 1.0)
            body.sensors["food_dz"] = _clamp(lz / 500.0, -1.0, 1.0)
            body.sensors["food_dist"] = max(0.0, 1.0 - dist / smell_range)

            body.sensors["smell"] = max(0.0, 1.0 - dist / smell_range)

            if dist < vision_range:
                target_yaw = math.atan2(dx, dz)
                target_pitch = math.atan2(dy, math.sqrt(dx * dx + dz * dz))

                dyaw = ((target_yaw - body.yaw + math.pi) % (2 * math.pi)) - math.pi
                dpitch = target_pitch - body.pitch

                vision_factor = max(0.0, 1.0 - dist / vision_range)
                pitch_factor = max(0.0, 1.0 - abs(dpitch) / 0.85)

                signal = vision_factor * pitch_factor

                center = max(0.0, 1.0 - abs(dyaw) / 0.45) * signal
                left = max(0.0, 1.0 - abs(dyaw + 0.55) / 0.75) * signal
                right = max(0.0, 1.0 - abs(dyaw - 0.55) / 0.75) * signal

                body.sensors["eye_center"] = max(body.sensors["eye_center"], center)
                body.sensors["eye_left"] = max(body.sensors["eye_left"], left)
                body.sensors["eye_right"] = max(body.sensors["eye_right"], right)

    margin = 75.0

    if body.x < margin:
        body.sensors["wall_left"] = 1.0 - body.x / margin

    if body.x > env.width - margin:
        body.sensors["wall_right"] = (body.x - (env.width - margin)) / margin

    if body.z < margin:
        body.sensors["wall_front"] = 1.0 - body.z / margin
    elif body.z > env.depth - margin:
        body.sensors["wall_front"] = (body.z - (env.depth - margin)) / margin

    floor_y = env.floor_height_at(body.x, body.z)
    body.sensors["floor_dist"] = _clamp((body.y - floor_y) / 300.0, 0.0, 1.0)
    body.sensors["ceiling_dist"] = _clamp((env.height - body.y) / 300.0, 0.0, 1.0)
    body.sensors["rand"] = GLOBAL_ENTROPY.random()
    body.sensors["speed"] = getattr(body, "last_step_speed", 0.0) / 10.0 # Normalized-ish

    # Algae proximity
    min_algae_dist = 1000.0
    for alg in env.algae:
        adx = alg["x"] - body.x
        ady = alg["y"] - body.y
        adz = alg["z"] - body.z
        adist = math.sqrt(adx*adx + ady*ady + adz*adz)
        if adist < min_algae_dist:
            min_algae_dist = adist
    body.sensors["algae_near"] = max(0.0, 1.0 - min_algae_dist / 150.0)

    # Current
    curr_time = getattr(env, "time", 0.0)
    cx, cy, cz = env.current_at(body.x, body.y, body.z, curr_time)

    # Local current
    cos_y = math.cos(body.yaw)
    sin_y = math.sin(body.yaw)
    body.sensors["current_x"] = _clamp((cx * cos_y - cz * sin_y) / 10.0, -1.0, 1.0)
    body.sensors["current_z"] = _clamp((cx * sin_y + cz * cos_y) / 10.0, -1.0, 1.0)
    body.sensors["current_y"] = _clamp(cy / 10.0, -1.0, 1.0)


def clamp_to_environment(body: Body, env: Environment, physics_config=None) -> bool:
    m = body.wall_margin
    hit = False
    body.last_collision = "none"

    # Wall X
    if body.x < m:
        body.x = m
        body.yaw = math.pi - body.yaw
        body.last_collision = "wall_x"
        hit = True
    elif body.x > env.width - m:
        body.x = env.width - m
        body.yaw = math.pi - body.yaw
        body.last_collision = "wall_x"
        hit = True

    # Wall Z
    if body.z < m:
        body.z = m
        body.yaw = -body.yaw
        body.last_collision = "wall_z"
        hit = True
    elif body.z > env.depth - m:
        body.z = env.depth - m
        body.yaw = -body.yaw
        body.last_collision = "wall_z"
        hit = True

    # Ceiling
    if body.y > env.height - m:
        body.y = env.height - m
        body.pitch = -abs(body.pitch)
        body.last_collision = "wall_y"
        hit = True

    # Floor (mesh)
    floor_y = env.floor_height_at(body.x, body.z) + 12.0
    if body.y < floor_y:
        body.y = floor_y
        body.pitch = abs(body.pitch)
        body.last_collision = "floor"
        hit = True

    if hit and physics_config is not None:
        body.energy = max(0.0, body.energy - physics_config.wall_penalty)

    return hit


def check_eat(body: Body, env: Environment) -> bool:
    eat_radius_sq = 900.0

    for i, food in enumerate(env.food):
        dx = food["x"] - body.x
        dy = food["y"] - body.y
        dz = food["z"] - body.z

        if dx * dx + dy * dy + dz * dz < eat_radius_sq:
            body.feed(food["energy"])
            env.remove_food(i)
            return True

    return False