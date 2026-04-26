import json
import logging
import multiprocessing as mp
import pickle
import queue
import time
from dataclasses import dataclass
from typing import Optional

import neat

from config.settings import EnvironmentConfig, PhysicsConfig
from evolution.runner import NEATRunner

logger = logging.getLogger(__name__)


@dataclass
class TrainingResult:
    ok: bool
    generation: int
    best_fitness: float
    best_genome_blob: Optional[bytes]
    duration_sec: float
    error: Optional[str] = None


def _worker_loop(
    command_queue: mp.Queue,
    result_queue: mp.Queue,
    neat_config_path: str,
    env_config: EnvironmentConfig,
    physics_config: PhysicsConfig,
):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    runner = NEATRunner(
        neat_config_path=neat_config_path,
        env_config=env_config,
        physics_config=physics_config,
    )
    # 👇 ЗАГРУЖАЕМ ЧЕКПОИНТ, ЕСЛИ ОН ЕСТЬ
    runner.load_checkpoint()

    alive = True

    while alive:
        try:
            command = command_queue.get()
        except KeyboardInterrupt:
            break

        action = command.get("action")

        if action == "stop":
            alive = False
            continue

        if action != "train":
            continue

        count = max(1, min(500, int(command.get("count", 1))))
        started = time.perf_counter()

        try:
            for _ in range(count):
                runner.run_next_generation()

            blob = pickle.dumps(runner.best_genome) if runner.best_genome else None

            result_queue.put(
                TrainingResult(
                    ok=True,
                    generation=runner.generation,
                    best_fitness=runner.best_fitness,
                    best_genome_blob=blob,
                    duration_sec=time.perf_counter() - started,
                )
            )

        except Exception as e:
            logger.exception("Training worker failed")
            result_queue.put(
                TrainingResult(
                    ok=False,
                    generation=runner.generation,
                    best_fitness=runner.best_fitness,
                    best_genome_blob=None,
                    duration_sec=time.perf_counter() - started,
                    error=str(e),
                )
            )


class TrainingProcess:
    # ... (без изменений) ...
    def __init__(
        self,
        neat_config_path: str,
        env_config: EnvironmentConfig,
        physics_config: PhysicsConfig,
    ):
        self.neat_config_path = neat_config_path
        self.env_config = env_config
        self.physics_config = physics_config

        self.ctx = mp.get_context("spawn")
        self.command_queue = self.ctx.Queue()
        self.result_queue = self.ctx.Queue()
        self.process: Optional[mp.Process] = None

        self.busy = False
        self.pending_generations = 0
        self.last_duration_sec = 0.0
        self.last_error = None

    def start(self):
        if self.process and self.process.is_alive():
            return

        self.process = self.ctx.Process(
            target=_worker_loop,
            args=(
                self.command_queue,
                self.result_queue,
                self.neat_config_path,
                self.env_config,
                self.physics_config,
            ),
            daemon=True,
        )
        self.process.start()

    def stop(self):
        try:
            self.command_queue.put({"action": "stop"})
        except Exception:
            pass

        if self.process:
            self.process.join(timeout=2.0)

            if self.process.is_alive():
                self.process.terminate()
                self.process.join(timeout=1.0)

    def train(self, count: int = 1):
        count = max(1, min(500, int(count)))
        self.start()

        if self.busy:
            self.pending_generations += count
            return

        self.busy = True
        self.command_queue.put({"action": "train", "count": count})

    def poll(self) -> Optional[TrainingResult]:
        try:
            result = self.result_queue.get_nowait()
        except queue.Empty:
            return None

        self.busy = False
        self.last_duration_sec = result.duration_sec
        self.last_error = result.error

        if self.pending_generations > 0:
            count = self.pending_generations
            self.pending_generations = 0
            self.train(count)

        return result