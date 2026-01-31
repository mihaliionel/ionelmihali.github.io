"""
Sistem scheduler pentru rularea automată și periodică a agentului de căutare cazări
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Callable, List, Optional
import schedule
import logging
from dataclasses import dataclass

@dataclass
class ScheduledTask:
    """Reprezentarea unei sarcini programate"""
    name: str
    function: Callable
    interval_type: str  # 'minutes', 'hours', 'days'
    interval_value: int
    next_run: datetime = None
    last_run: datetime = None
    is_running: bool = False
    enabled: bool = True
    
    def __post_init__(self):
        if self.next_run is None:
            self.next_run = datetime.now()

class AccommodationScheduler:
    """Scheduler principal pentru agentul de căutare cazări"""
    
    def __init__(self):
        self.tasks: List[ScheduledTask] = []
        self.is_running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.logger = logging.getLogger(__name__)
        
        # Setup logging
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def add_task(self, task: ScheduledTask):
        """Adaugă o sarcină nouă în scheduler"""
        self.tasks.append(task)
        self.logger.info(f"Adăugată sarcina: {task.name} - rulează la fiecare {task.interval_value} {task.interval_type}")
    
    def remove_task(self, task_name: str) -> bool:
        """Elimină o sarcină din scheduler"""
        for i, task in enumerate(self.tasks):
            if task.name == task_name:
                del self.tasks[i]
                self.logger.info(f"Eliminată sarcina: {task_name}")
                return True
        return False
    
    def enable_task(self, task_name: str) -> bool:
        """Activează o sarcină"""
        for task in self.tasks:
            if task.name == task_name:
                task.enabled = True
                self.logger.info(f"Activată sarcina: {task_name}")
                return True
        return False
    
    def disable_task(self, task_name: str) -> bool:
        """Dezactivează o sarcină"""
        for task in self.tasks:
            if task.name == task_name:
                task.enabled = False
                self.logger.info(f"Dezactivată sarcina: {task_name}")
                return True
        return False
    
    def _calculate_next_run(self, task: ScheduledTask) -> datetime:
        """Calculează următoarea execuție pentru o sarcină"""
        now = datetime.now()
        
        if task.interval_type == 'minutes':
            return now + timedelta(minutes=task.interval_value)
        elif task.interval_type == 'hours':
            return now + timedelta(hours=task.interval_value)
        elif task.interval_type == 'days':
            return now + timedelta(days=task.interval_value)
        else:
            return now + timedelta(hours=1)  # Default la 1 oră
    
    def _run_task(self, task: ScheduledTask):
        """Execută o sarcină"""
        if not task.enabled or task.is_running:
            return
        
        task.is_running = True
        task.last_run = datetime.now()
        
        try:
            self.logger.info(f"Execuție sarcină: {task.name}")
            task.function()
            self.logger.info(f"Sarcina {task.name} completată cu succes")
        except Exception as e:
            self.logger.error(f"Eroare la execuția sarcinii {task.name}: {e}")
        finally:
            task.is_running = False
            task.next_run = self._calculate_next_run(task)
    
    def _scheduler_loop(self):
        """Loop-ul principal al scheduler-ului"""
        self.logger.info("Scheduler pornit")
        
        while self.is_running:
            now = datetime.now()
            
            # Verifică fiecare sarcină
            for task in self.tasks:
                if (task.enabled and 
                    not task.is_running and 
                    now >= task.next_run):
                    
                    # Execută sarcina într-un thread separat
                    task_thread = threading.Thread(
                        target=self._run_task, 
                        args=(task,),
                        name=f"Task-{task.name}"
                    )
                    task_thread.daemon = True
                    task_thread.start()
            
            # Pauză scurtă pentru a nu suprasolicita CPU-ul
            time.sleep(30)  # Verifică la fiecare 30 de secunde
        
        self.logger.info("Scheduler oprit")
    
    def start(self):
        """Pornește scheduler-ul"""
        if self.is_running:
            self.logger.warning("Scheduler-ul rulează already")
            return
        
        self.is_running = True
        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            name="AccommodationScheduler"
        )
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
        
        self.logger.info(f"Scheduler pornit cu {len(self.tasks)} sarcini")
    
    def stop(self):
        """Oprește scheduler-ul"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
        
        self.logger.info("Scheduler oprit")
    
    def get_status(self) -> dict:
        """Returnează statusul scheduler-ului și al sarcinilor"""
        status = {
            'scheduler_running': self.is_running,
            'total_tasks': len(self.tasks),
            'enabled_tasks': sum(1 for task in self.tasks if task.enabled),
            'running_tasks': sum(1 for task in self.tasks if task.is_running),
            'tasks': []
        }
        
        for task in self.tasks:
            task_info = {
                'name': task.name,
                'enabled': task.enabled,
                'is_running': task.is_running,
                'interval': f"{task.interval_value} {task.interval_type}",
                'last_run': task.last_run.isoformat() if task.last_run else None,
                'next_run': task.next_run.isoformat() if task.next_run else None
            }
            status['tasks'].append(task_info)
        
        return status

class TaskBuilder:
    """Builder pentru crearea sarcinilor programate"""
    
    @staticmethod
    def search_task(search_function: Callable, interval_hours: int = 6) -> ScheduledTask:
        """Creează o sarcină de căutare periodică"""
        return ScheduledTask(
            name="accommodation_search",
            function=search_function,
            interval_type="hours",
            interval_value=interval_hours
        )
    
    @staticmethod
    def price_alert_task(alert_function: Callable, interval_minutes: int = 30) -> ScheduledTask:
        """Creează o sarcină pentru verificarea alertelor de preț"""
        return ScheduledTask(
            name="price_alerts",
            function=alert_function,
            interval_type="minutes",
            interval_value=interval_minutes
        )
    
    @staticmethod
    def cleanup_task(cleanup_function: Callable, interval_days: int = 1) -> ScheduledTask:
        """Creează o sarcină pentru curățarea datelor vechi"""
        return ScheduledTask(
            name="database_cleanup",
            function=cleanup_function,
            interval_type="days",
            interval_value=interval_days
        )
    
    @staticmethod
    def heartbeat_task(heartbeat_function: Callable, interval_minutes: int = 15) -> ScheduledTask:
        """Creează o sarcină de heartbeat pentru monitorizare"""
        return ScheduledTask(
            name="system_heartbeat",
            function=heartbeat_function,
            interval_type="minutes",
            interval_value=interval_minutes
        )

class SchedulerConfig:
    """Configurația pentru scheduler"""
    
    def __init__(self):
        self.search_interval_hours = 6
        self.price_alert_interval_minutes = 30
        self.cleanup_interval_days = 1
        self.heartbeat_interval_minutes = 15
        self.max_concurrent_tasks = 3
        self.enable_logging = True
        self.log_level = "INFO"
    
    @classmethod
    def from_dict(cls, config_dict: dict):
        """Creează configurația din dicționar"""
        config = cls()
        
        for key, value in config_dict.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        return config

def create_default_scheduler(search_function: Callable, 
                           alert_function: Callable,
                           cleanup_function: Callable,
                           config: SchedulerConfig = None) -> AccommodationScheduler:
    """Creează un scheduler cu sarcinile implicite"""
    
    if config is None:
        config = SchedulerConfig()
    
    scheduler = AccommodationScheduler()
    
    # Adaugă sarcinile standard
    scheduler.add_task(TaskBuilder.search_task(search_function, config.search_interval_hours))
    scheduler.add_task(TaskBuilder.price_alert_task(alert_function, config.price_alert_interval_minutes))
    scheduler.add_task(TaskBuilder.cleanup_task(cleanup_function, config.cleanup_interval_days))
    
    # Heartbeat pentru a verifica că sistemul funcționează
    def heartbeat():
        logging.getLogger("heartbeat").info("System is alive")
    
    scheduler.add_task(TaskBuilder.heartbeat_task(heartbeat, config.heartbeat_interval_minutes))
    
    return scheduler

# Funcții utilitare
def setup_scheduler_logging(log_level: str = "INFO"):
    """Configurează logging-ul pentru scheduler"""
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('accommodation_agent.log')
        ]
    )

def run_scheduler_daemon(scheduler: AccommodationScheduler, pid_file: str = "scheduler.pid"):
    """Rulează scheduler-ul ca daemon (Windows compatible)"""
    import os
    import signal
    import atexit
    
    def cleanup():
        scheduler.stop()
        if os.path.exists(pid_file):
            os.remove(pid_file)
    
    def signal_handler(signum, frame):
        cleanup()
        exit(0)
    
    # Înregistrează cleanup-ul
    atexit.register(cleanup)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Scrie PID-ul
    with open(pid_file, 'w') as f:
        f.write(str(os.getpid()))
    
    # Pornește scheduler-ul
    scheduler.start()
    
    try:
        # Ține programul în viață
        while scheduler.is_running:
            time.sleep(1)
    except KeyboardInterrupt:
        cleanup()