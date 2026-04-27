import copy
import json
import logging
import pickle
from pathlib import Path
from typing import Optional

import neat

from config.settings import EnvironmentConfig, PhysicsConfig

logger = logging.getLogger(__name__)

CHECKPOINT_FILE = "checkpoint.json"


class NEATRunner:
    def __init__(
        self,
        neat_config_path: str,
        env_config: EnvironmentConfig,
        physics_config: PhysicsConfig,
    ):
        self.neat_config = neat.Config(
            neat.DefaultGenome,
            neat.DefaultReproduction,
            neat.DefaultSpeciesSet,
            neat.DefaultStagnation,
            neat_config_path,
        )
        self.env_config = env_config
        self.physics_config = physics_config
        self.population = neat.Population(self.neat_config)
        self.stats = neat.StatisticsReporter()
        self.population.add_reporter(self.stats)
        self.population.add_reporter(neat.StdOutReporter(True))

        self.generation = 0
        self.best_genome: Optional[neat.DefaultGenome] = None
        self.best_fitness = -999999.0
        self.best_net = None

    def run_next_generation(self):
        """Одно полноценное поколение (оценка + размножение)."""
        self._current_avg_fitness = 0.0

        # Локальная функция для передачи в population.run
        def eval_genomes(genomes, config):
            from .evaluator import evaluate_genome
            total_fitness = 0.0
            for genome_id, genome in genomes:
                fitness, _, _ = evaluate_genome(
                    genome,
                    config,
                    self.env_config,
                    self.physics_config,
                    max_steps=2000,
                )
                genome.fitness = fitness
                total_fitness += fitness
            if genomes:
                self._current_avg_fitness = total_fitness / len(genomes)

        # Главный вызов: оценка + скрещивание + мутации
        self.population.run(eval_genomes, 1)

        # Синхронизируем номер поколения
        self.generation = self.population.generation

        best = self.population.best_genome
        if best is None:
            logger.warning("best_genome is None after generation")
            return

        logger.info(f"Gen {self.generation} | Avg: {self._current_avg_fitness:.1f} | Best: {best.fitness:.1f}")

        if best.fitness > self.best_fitness:
            from .evaluator import create_net
            self.best_fitness = best.fitness
            self.best_genome = copy.deepcopy(best)
            self.best_net = create_net(self.best_genome, self.neat_config)
            self.save_checkpoint()
            logger.info(f"*** NEW BEST: {self.best_fitness:.1f} ***")

    def _config_hash(self):
        import hashlib
        c = self.neat_config.genome_config
        s = f"{c.num_inputs}|{c.num_outputs}|{c.initial_connection}"
        return hashlib.md5(s.encode()).hexdigest()

    def save_checkpoint(self):
        try:
            with open("best_genome.pkl", "wb") as f:
                pickle.dump(self.best_genome, f)
            data = {
                "generation": self.generation,
                "best_fitness": self.best_fitness,
                "config_hash": self._config_hash(),
                "input_size": self.neat_config.genome_config.num_inputs,
                "output_size": self.neat_config.genome_config.num_outputs,
            }
            with open(CHECKPOINT_FILE, "w") as f:
                json.dump(data, f)
            logger.info("Чекпоинт сохранён: поколение %d, фитнес %.1f", self.generation, self.best_fitness)
        except Exception as e:
            logger.error(f"Ошибка сохранения чекпоинта: {e}")

    def load_checkpoint(self):
        if not Path("best_genome.pkl").exists():
            logger.info("Чекпоинт не найден, стартуем с нуля")
            return
        try:
            if Path(CHECKPOINT_FILE).exists():
                with open(CHECKPOINT_FILE) as f:
                    data = json.load(f)

                # Validation
                current_hash = self._config_hash()
                saved_hash = data.get("config_hash")
                if saved_hash and saved_hash != current_hash:
                    logger.warning("Checkpoint config hash mismatch! Ignoring old checkpoint.")
                    return

                self.generation = data.get("generation", 0)
                self.best_fitness = data.get("best_fitness", -999999.0)
            else:
                self.generation = 0
                self.best_fitness = 0.0

            from .evaluator import create_net
            with open("best_genome.pkl", "rb") as f:
                self.best_genome = pickle.load(f)
            self.best_net = create_net(self.best_genome, self.neat_config)

            logger.info("Чекпоинт загружен: поколение %d, фитнес %.1f", self.generation, self.best_fitness)
        except Exception as e:
            logger.error(f"Ошибка загрузки чекпоинта: {e}, стартуем с нуля")
            self.best_genome = None
            self.best_net = None
            self.generation = 0
            self.best_fitness = -999999.0

    def get_best_net(self):
        return self.best_net