import random

def criar_perfil_navegador():
    """Cria um perfil de navegador com características realistas."""
    webgl_vendors = [
        {"vendor": "Google Inc.", "renderer": "ANGLE (Intel, Mesa Intel(R) HD Graphics 520 (KBL GT2), OpenGL 4.6)"},
        {"vendor": "Intel Inc.", "renderer": "Intel Iris OpenGL Engine"},
        {"vendor": "NVIDIA Corporation", "renderer": "NVIDIA GeForce RTX 3060/PCIe/SSE2"},
    ]
    
    perfis = [
        {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "platform": "Win32",
            "resolution": (1920, 1080),
            "webgl": random.choice(webgl_vendors),
            "device_memory": 8,
            "hardware_concurrency": 8,
            "touch_points": 0
        },
        {
            "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "platform": "Linux x86_64",
            "resolution": (2560, 1440),
            "webgl": random.choice(webgl_vendors),
            "device_memory": 16,
            "hardware_concurrency": 12,
            "touch_points": 0
        }
    ]
    return random.choice(perfis)