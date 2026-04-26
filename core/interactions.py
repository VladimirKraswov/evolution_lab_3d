import math
from .body import Body
from .environment import Environment
from services import GLOBAL_ENTROPY

def update_sensors(body: Body, env: Environment):
    for key in ["eye_left","eye_center","eye_right","smell","wall_left","wall_right","wall_front","food_dx","food_dy","food_dz","food_dist"]:
        body.sensors[key] = 0.0

    if env.food:
        nearest_dist_sq, nearest_food = float("inf"), None
        for food in env.food:
            dx,dy,dz = food["x"]-body.x, food["y"]-body.y, food["z"]-body.z
            d_sq = dx*dx+dy*dy+dz*dz
            if d_sq < nearest_dist_sq: nearest_dist_sq, nearest_food = d_sq, food

        if nearest_food is not None:
            dist = math.sqrt(nearest_dist_sq)
            dx, dy, dz = nearest_food["x"]-body.x, nearest_food["y"]-body.y, nearest_food["z"]-body.z

            # Local coordinate system transformation (simplified)
            # Yaw rotation (around Y)
            cos_y, sin_y = math.cos(-body.yaw), math.sin(-body.yaw)
            lx = dx * cos_y - dz * sin_y
            lz = dx * sin_y + dz * cos_y

            # Pitch rotation (around X)
            cos_p, sin_p = math.cos(-body.pitch), math.sin(-body.pitch)
            ly = dy * cos_p + lz * sin_p
            lz = -dy * sin_p + lz * cos_p

            body.sensors["food_dx"] = max(-1.0, min(1.0, lx / 200.0))
            body.sensors["food_dy"] = max(-1.0, min(1.0, ly / 200.0))
            body.sensors["food_dz"] = max(-1.0, min(1.0, lz / 200.0))
            body.sensors["food_dist"] = max(0.0, 1.0 - dist / 500.0)

            body.sensors["smell"] = max(0.0, 1.0 - dist / 150.0)
            if dist < 180:
                target_yaw = math.atan2(dx, dz)
                target_pitch = math.atan2(dy, math.sqrt(dx*dx+dz*dz))
                dyaw = ((target_yaw - body.yaw + math.pi) % (2*math.pi)) - math.pi
                dpitch = target_pitch - body.pitch
                vision_factor = max(0.0, 1.0 - dist / 180.0)
                if dyaw < -0.15: body.sensors["eye_left"] = vision_factor * min(1.0, abs(dyaw) / 0.8)
                elif dyaw > 0.15: body.sensors["eye_right"] = vision_factor * min(1.0, abs(dyaw) / 0.8)
                if abs(dyaw) < 0.4 and abs(dpitch) < 0.3: body.sensors["eye_center"] = vision_factor * (1.0 - abs(dyaw) / 0.4)

    body.sensors["floor_dist"] = max(0.0, 1.0 - body.y / 200.0)
    body.sensors["ceiling_dist"] = max(0.0, 1.0 - (env.height - body.y) / 200.0)
    body.sensors["energy"] = body.energy / body.max_energy
    body.sensors["speed_sensor"] = body.last_speed

    cx, cy, cz = env.current_at(body.x, body.y, body.z)
    body.sensors["current_x"] = max(-1.0, min(1.0, cx / 10.0))
    body.sensors["current_z"] = max(-1.0, min(1.0, cz / 10.0))

    margin = 50.0
    if body.x < margin: body.sensors["wall_left"] = 1.0 - body.x / margin
    if body.x > env.width - margin: body.sensors["wall_right"] = (body.x - (env.width - margin)) / margin
    if body.z < margin: body.sensors["wall_front"] = 1.0 - body.z / margin
    elif body.z > env.depth - margin: body.sensors["wall_front"] = (body.z - (env.depth - margin)) / margin
    body.sensors["rand"] = GLOBAL_ENTROPY.random()

def check_eat(body: Body, env: Environment) -> bool:
    for i, food in enumerate(env.food):
        dx,dy,dz = food["x"]-body.x, food["y"]-body.y, food["z"]-body.z
        if dx*dx+dy*dy+dz*dz < 500:
            body.feed(food["energy"]); env.remove_food(i); return True
    return False
