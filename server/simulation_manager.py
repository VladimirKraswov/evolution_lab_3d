import asyncio
import logging
import math
import pickle
import time
from typing import Optional

from core import Body, Environment, update_sensors, check_eat, clamp_to_environment
from config.settings import AppConfig
from evolution.runner import NEATRunner
from evolution.training_process import TrainingProcess
from services import GLOBAL_ENTROPY

logger = logging.getLogger(__name__)


class SimulationManager:
    def __init__(
        self,
        config: AppConfig,
        neat_runner: NEATRunner,
        training_process: Optional[TrainingProcess] = None,
    ):
        self.config = config
        self.runner = neat_runner
        self.training_process = training_process

        self.env = Environment(config.env)
        self.body: Optional[Body] = None
        self.visualization_data = None

        self.demo_active = False
        self.demo_steps = 0
        self.max_demo_steps = 2000

        self.sim_hz = getattr(config, "sim_hz", 90)
        self.broadcast_hz = getattr(config, "broadcast_hz", 30)

        self.command_queue: asyncio.Queue = asyncio.Queue()

        self.sequence = 0
        self.last_step_distance = 0.0
        self.last_cmd = {}
        self.last_inputs = []
        self.last_outputs = []

        self._idle_steps = 0
        self._last_entropy_refresh = 0.0
        self._entropy_task = None

    def _init_demo(self):
        self.env.reset(initial_food=self.config.env.initial_food_count)
        self.body = Body.random_placement(
            self.config.physics,
            env_width=self.env.width,
            env_height=self.env.height,
            env_depth=self.env.depth,
        )
        clamp_to_environment(self.body, self.env, self.config.physics)

        self.demo_steps = 0
        self.demo_active = True
        self._idle_steps = 0
        self.last_step_distance = 0.0
        self.last_cmd = {}
        self.last_inputs = []
        self.last_outputs = []

        logger.info(
            "Demo restarted at (%.0f, %.0f, %.0f)",
            self.body.x,
            self.body.y,
            self.body.z,
        )

    async def _wait_training_and_apply(self):
        """
        Ждёт результат обучения и применяет лучший genome.

        Важно:
        TrainingProcess.poll() может автоматически запустить pending generations.
        Поэтому если после результата worker снова busy, не стартуем демо,
        а ждём финальный результат очереди.
        """
        if self.training_process is None:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self.runner.run_next_generation)
            return

        while True:
            result = self.training_process.poll()

            if result is not None:
                if result.ok and result.best_genome_blob is not None:
                    from evolution.evaluator import create_net

                    genome = pickle.loads(result.best_genome_blob)

                    self.runner.best_genome = genome
                    self.runner.best_net = create_net(
                        genome,
                        self.runner.neat_config,
                    )
                    self.runner.best_fitness = result.best_fitness
                    self.runner.generation = result.generation

                    logger.info(
                        "Получен результат поколения %d (fitness=%.1f)",
                        result.generation,
                        result.best_fitness,
                    )
                else:
                    logger.error("Ошибка обучения: %s", result.error)

                if not self.training_process.busy:
                    return

            await asyncio.sleep(0.2)

    async def _ensure_trained_generation(self):
        if self.runner.best_net is not None:
            return

        if self.training_process is not None:
            self.training_process.train(count=1)
            logger.info("Запрошено обучение первого поколения в фоновом процессе")

        await self._wait_training_and_apply()

    async def run_loop(self, ws_handler):
        try:
            await self._ensure_trained_generation()

            self._init_demo()
            logger.info("Демонстрационный режим запущен")

            self._entropy_task = asyncio.create_task(self._entropy_refresh_loop())

            last_broadcast = 0.0
            last_clients_count = 0

            while True:
                now = time.perf_counter()

                await self._handle_pending_commands()

                if self.demo_active and self.body and self.runner.best_net:
                    self._update_demo(1.0 / self.sim_hz)

                    current_clients_count = len(ws_handler.clients)
                    if now - last_broadcast >= 1.0 / self.broadcast_hz:
                        is_init = current_clients_count > last_clients_count
                        self.visualization_data = self._build_viz_data(now, is_init=is_init)
                        await ws_handler.broadcast(self.visualization_data)
                        last_broadcast = now
                        last_clients_count = current_clients_count

                else:
                    logger.info("Демо завершено → запускаем следующее поколение")

                    if self.training_process is not None:
                        if not self.training_process.busy:
                            self.training_process.train(count=1)

                    await self._wait_training_and_apply()
                    self._init_demo()

                await asyncio.sleep(1.0 / self.sim_hz)

        except asyncio.CancelledError:
            logger.info("run_loop остановлен")
        except Exception as e:
            logger.critical("Критическая ошибка в run_loop: %s", e, exc_info=True)
        finally:
            if self._entropy_task and not self._entropy_task.done():
                self._entropy_task.cancel()

    async def _entropy_refresh_loop(self):
        while True:
            try:
                await asyncio.wait_for(GLOBAL_ENTROPY.refresh(), timeout=4.0)
            except asyncio.TimeoutError:
                logger.warning("Timeout при получении энтропии")
            except Exception as e:
                logger.warning("Ошибка обновления энтропии: %s", e)

            await asyncio.sleep(20.0)

    async def _handle_pending_commands(self):
        handled = 0

        while not self.command_queue.empty() and handled < 20:
            try:
                command = await self.command_queue.get()
                action = command.get("action")

                if action == "reset_demo":
                    self._init_demo()

                elif action == "next_gen":
                    self.demo_active = False

                elif action == "skip_gens":
                    count = max(1, min(500, int(command.get("count", 1))))

                    if self.training_process is not None:
                        self.training_process.train(count=count)

                    self.demo_active = False

                elif action == "reset_training":
                    logger.info("Resetting training requested")
                    if self.training_process is not None:
                        self.training_process.stop()

                    import os
                    for f in ["best_genome.pkl", "checkpoint.json"]:
                        if os.path.exists(f):
                            os.remove(f)

                    # Re-init runner and process
                    from evolution.runner import NEATRunner
                    self.runner = NEATRunner(
                        self.runner.neat_config_path if hasattr(self.runner, "neat_config_path") else "neat_config.ini",
                        self.config.env,
                        self.config.physics
                    )
                    if self.training_process is not None:
                        from evolution.training_process import TrainingProcess
                        self.training_process = TrainingProcess(
                            self.runner.neat_config_path if hasattr(self.runner, "neat_config_path") else "neat_config.ini",
                            self.config.env,
                            self.config.physics
                        )

                    self.demo_active = False

                handled += 1

            except Exception as e:
                logger.warning("Ошибка обработки команды: %s", e)

    def _update_demo(self, dt: float):
        if not self.body or not self.demo_active:
            return

        if self.body.energy <= 0 or self.demo_steps >= self.max_demo_steps:
            self.demo_active = False
            return

        now = time.perf_counter()
        self.env.time = now

        # Update drifting food
        for food in self.env.food:
            seed = food.get("drift_seed", 0.0)
            food["x"] += math.sin(now * 0.4 + seed) * 0.15
            food["z"] += math.cos(now * 0.3 + seed) * 0.15

        update_sensors(self.body, self.env)

        from evolution.evaluator import brain_inputs
        inputs = brain_inputs(self.body.get_sensors())

        self.last_inputs = [float(x) for x in inputs]

        output = self.runner.best_net.activate(inputs)
        self.last_outputs = [float(x) for x in output]

        move_raw = float(output[0]) if len(output) > 0 else 0.0

        cmd = {
            "forward": max(0.0, min(1.0, move_raw)) if move_raw > 0.03 else 0.0,
            "backward": max(0.0, min(1.0, -move_raw)) if move_raw < -0.2 else 0.0,
            "turbo": 1.0 if len(output) > 4 and float(output[4]) > 0.72 else 0.0,
            "yaw": float(output[1]) if len(output) > 1 else 0.0,
            "pitch": float(output[2]) * 0.45 if len(output) > 2 else 0.0,
            "roll": float(output[3]) * 0.35 if len(output) > 3 else 0.0,
        }

        self.last_cmd = cmd

        before_x = self.body.x
        before_y = self.body.y
        before_z = self.body.z

        self.body.update(dt, cmd)

        # Apply current and algae drag
        cx, cy, cz = self.env.current_at(self.body.x, self.body.y, self.body.z, self.env.time)
        self.body.x += cx * 0.2 * dt
        self.body.y += cy * 0.2 * dt
        self.body.z += cz * 0.2 * dt

        algae_factor = self.body.sensors.get("algae_near", 0.0)
        if algae_factor > 0.1:
            drag = 1.0 - algae_factor * 0.4
            self.body.x = before_x + (self.body.x - before_x) * drag
            self.body.y = before_y + (self.body.y - before_y) * drag
            self.body.z = before_z + (self.body.z - before_z) * drag

        # clamp_to_environment теперь обрабатывает и стены, и пол, и потолок
        clamp_to_environment(self.body, self.env, self.config.physics)

        dx = self.body.x - before_x
        dy = self.body.y - before_y
        dz = self.body.z - before_z

        self.last_step_distance = (dx * dx + dy * dy + dz * dz) ** 0.5
        self.body.last_step_speed = self.last_step_distance / dt
        self.body.sensors["energy_status"] = self.body.energy / self.body.max_energy

        if check_eat(self.body, self.env):
            self.demo_steps = max(0, self.demo_steps - int(self.sim_hz * 3))

        self.demo_steps += 1

        if self.demo_steps % (self.sim_hz * 5) == 0 and len(self.env.food) < 20:
            self.env.spawn_food(1)

    def _build_viz_data(self, now: float, is_init: bool = False):
        if not self.body:
            return None

        env_state = self.env.get_state()
        if not is_init:
            # For snapshots, remove static data
            env_state.pop("terrain", None)
            env_state.pop("algae", None)

        return {
            "type": "init" if is_init else "snapshot",
            "timestamp": now,
            "environment": env_state,
            "body": self.body.get_state(),
            "sensors": self.body.get_sensors(),
            "gen": self.runner.generation,
            "best_fitness": self.runner.best_fitness,
            "demo_steps": self.demo_steps,
            "last_cmd": self.last_cmd,
            "last_outputs": self.last_outputs,
            "brain": self._genome_to_graph(self.runner.best_genome),
            "training_busy": self.training_process.busy if self.training_process else False,
            "pending_generations": self.training_process.pending_generations if self.training_process else 0,
            "entropy": {
                "source": GLOBAL_ENTROPY.last_source,
                "pool": len(GLOBAL_ENTROPY.pool),
            },
        }

    def _genome_to_graph(self, genome):
        if genome is None:
            return {
                "nodes": [],
                "connections": [],
                "stats": {
                    "total_connections": 0,
                    "enabled_connections": 0,
                    "disabled_connections": 0,
                },
            }

        nodes = []
        connections = []

        input_labels = [
            "hunger", "eye_L", "eye_C", "eye_R", "smell",
            "wall_L", "wall_R", "wall_F", "memory", "novelty",
            "stuck", "rand", "food_dx", "food_dy", "food_dz",
            "food_dist", "floor", "ceil", "algae", "speed",
            "curr_x", "curr_y", "curr_z", "energy"
        ]

        output_labels = ["move", "yaw", "pitch", "roll", "turbo", "mem"]

        last_inputs = self.last_inputs or []
        last_outputs = self.last_outputs or []

        for i, label in enumerate(input_labels):
            nodes.append({
                "id": -i - 1,
                "layer": 0,
                "label": label,
                "type": "input",
                "activation": float(last_inputs[i]) if i < len(last_inputs) else 0.0,
            })

        output_ids = set(range(len(output_labels)))

        for i, label in enumerate(output_labels):
            nodes.append({
                "id": i,
                "layer": 2,
                "label": label,
                "type": "output",
                "activation": float(last_outputs[i]) if i < len(last_outputs) else 0.0,
            })

        for node_id, node in genome.nodes.items():
            if node_id in output_ids:
                continue

            nodes.append({
                "id": int(node_id),
                "layer": 1,
                "label": f"h{node_id}",
                "type": "hidden",
                "activation": 0.0,
                "bias": float(getattr(node, "bias", 0.0)),
            })

        enabled_count = 0
        disabled_count = 0

        for conn_key, conn in genome.connections.items():
            enabled = bool(conn.enabled)

            if enabled:
                enabled_count += 1
            else:
                disabled_count += 1

            connections.append({
                "from": int(conn_key[0]),
                "to": int(conn_key[1]),
                "weight": float(conn.weight),
                "enabled": enabled,
            })

        return {
            "nodes": nodes,
            "connections": connections,
            "stats": {
                "total_connections": len(connections),
                "enabled_connections": enabled_count,
                "disabled_connections": disabled_count,
            },
        }