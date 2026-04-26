import asyncio
import multiprocessing
from config.settings import CONFIG
from evolution.training_process import TrainingProcess
from server.simulation_manager import SimulationManager
from server.app import create_app
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

async def main():
    # Отдельный процесс для обучения NEAT
    training_process = TrainingProcess(
        neat_config_path="neat_config.ini",
        env_config=CONFIG.env,
        physics_config=CONFIG.physics,
    )
    training_process.start()

    # Лёгкий runner – будет загружать чекпоинт, если он есть
    from evolution.runner import NEATRunner

    runner = NEATRunner("neat_config.ini", CONFIG.env, CONFIG.physics)
    runner.load_checkpoint()   # <-- загружаем лучшую сеть и поколение

    sim_manager = SimulationManager(
        config=CONFIG,
        neat_runner=runner,
        training_process=training_process,
    )

    app = create_app(sim_manager, runner)

    import uvicorn

    config = uvicorn.Config(app, host=CONFIG.host, port=CONFIG.port, log_level="info")
    server = uvicorn.Server(config)

    await server.serve()

if __name__ == "__main__":
    multiprocessing.set_start_method("spawn", force=True)
    asyncio.run(main())