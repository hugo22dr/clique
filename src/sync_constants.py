import os
import fcntl
import struct

# Define as constantes IOCTL
# Deve corresponder aos valores definidos no kernel module
CLICK_SYNC_MAGIC = ord('k')

def _IOW(type, nr, size):
    """Recria a macro _IOW do kernel."""
    direction = 1  # Write
    size = struct.calcsize(size)
    return (direction << 30) | (size << 16) | (type << 8) | nr

# Comandos IOCTL que correspondem ao módulo do kernel
PRECISE_SYNC_SET_THREADS = _IOW(CLICK_SYNC_MAGIC, 1, 'i')
PRECISE_SYNC_WAIT = _IOW(CLICK_SYNC_MAGIC, 2, 'L')

class SyncDevice:
    def __init__(self):
        self.fd = os.open("/dev/precise_sync", os.O_RDWR)
    
    def wait_sync(self):
        """Executa a sincronização precisa."""
        return fcntl.ioctl(self.fd, PRECISE_SYNC_WAIT, 0)
    
    def set_threads(self, num_threads):
        """Configura o número de threads para sincronização."""
        return fcntl.ioctl(self.fd, PRECISE_SYNC_SET_THREADS, num_threads)
    
    def __del__(self):
        try:
            os.close(self.fd)
        except:
            pass

# Exporta as constantes e classe para uso
__all__ = [
    'PRECISE_SYNC_SET_THREADS',
    'PRECISE_SYNC_WAIT',
    'SyncDevice'
]