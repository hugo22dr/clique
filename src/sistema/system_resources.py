from dataclasses import dataclass
import os
import psutil

@dataclass
class SystemResources:
    total_cores: int
    logical_processors: int
    available_memory: int
    process_id: int

def get_system_resources() -> SystemResources:
    """Coleta informações sobre os recursos do sistema."""
    return SystemResources(
        total_cores=psutil.cpu_count(logical=False),
        logical_processors=psutil.cpu_count(logical=True),
        available_memory=psutil.virtual_memory().available,
        process_id=os.getpid()
    )
