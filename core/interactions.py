import math
from .body import Body
from .environment import Environment
from services import GLOBAL_ENTROPY

def update_sensors(body: Body, env: Environment):
    for key in ["eye_left","eye_center","eye_right","smell","wall_left","wall_right","wall_front"]: body.sensors[key] = 0.0
    if env.food:
        nearest_dist, nearest_food = float("inf"), None
        for food in env.food:
            dx,dy,dz = food["x"]-body.x, food["y"]-body.y, food["z"]-body.z
            dist_sq = dx*dx+dy*dy+dz*dz
            if dist_sq < nearest_dist: nearest_dist, nearest_food = dist_sq, food
        if nearest_food is not None and nearest_dist > 0:
            dx,dy,dz = nearest_food["x"]-body.x, nearest_food["y"]-body.y, nearest_food["z"]-body.z
            dist = math.sqrt(nearest_dist)
            body.sensors["smell"] = max(0.0, 1.0 - dist / 150.0)
            if dist < 180:
                target_yaw = math.atan2(dx, dz); target_pitch = math.atan2(dy, math.sqrt(dx*dx+dz*dz))
                dyaw = ((target_yaw - body.yaw + math.pi) % (2*math.pi)) - math.pi; dpitch = target_pitch - body.pitch
                vision_factor = max(0.0, 1.0 - dist / 180.0)
                if dyaw < -0.15: body.sensors["eye_left"] = vision_factor * min(1.0, abs(dyaw) / 0.8)
                elif dyaw > 0.15: body.sensors["eye_right"] = vision_factor * min(1.0, abs(dyaw) / 0.8)
                if abs(dyaw) < 0.4 and abs(dpitch) < 0.3: body.sensors["eye_center"] = vision_factor * (1.0 - abs(dyaw) / 0.4)
    margin = 50.0
    if body.x < margin: body.sensors["wall_left"] = 1.0 - body.x / margin
    if body.x > 800 - margin: body.sensors["wall_right"] = (body.x - (800 - margin)) / margin
    if body.z < margin: body.sensors["wall_front"] = 1.0 - body.z / margin
    elif body.z > 800 - margin: body.sensors["wall_front"] = (body.z - (800 - margin)) / margin
    body.sensors["rand"] = GLOBAL_ENTROPY.random()

def check_eat(body: Body, env: Environment) -> bool:
    for i, food in enumerate(env.food):
        dx,dy,dz = food["x"]-body.x, food["y"]-body.y, food["z"]-body.z
        if dx*dx+dy*dy+dz*dz < 500:
            body.feed(food["energy"]); env.remove_food(i); return True
    return False
