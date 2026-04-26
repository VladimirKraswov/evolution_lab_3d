import math

from .body import Body
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

    body.sensors["rand"] = GLOBAL_ENTROPY.random()


def clamp_to_environment(body: Body, env: Environment, physics_config=None) -> bool:
    floor_y = env.floor_height_at(body.x, body.z) + 12.0

    if body.y < floor_y:
        body.y = floor_y
        body.pitch = abs(body.pitch)

        if physics_config is not None:
            body.energy = max(0.0, body.energy - physics_config.wall_penalty * 0.35)

        return True

    return False


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