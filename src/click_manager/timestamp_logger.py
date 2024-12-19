import time

class PreciseTimestampLogger:
    def __init__(self, logger):
        self.logger = logger
        self.timestamps = []
        self.click_timestamps = []
        self.has_tsc = False
        
        # Tenta importar click_sync mas não falha se não conseguir
        try:
            import click_sync
            self.click_sync = click_sync
            # Tenta ler TSC para verificar se está funcionando
            try:
                self.click_sync.read_tsc()
                self.has_tsc = True
            except:
                self.has_tsc = False
        except:
            self.click_sync = None
            self.has_tsc = False
        
    def log_timestamp(self, event_name, driver_id):
        """Registra timestamps precisos."""
        timestamp = {
            'event': event_name,
            'driver_id': driver_id,
            'monotonic_ns': time.monotonic_ns(),
            'process_time_ns': time.process_time_ns(),
            'thread_time_ns': time.thread_time_ns()
        }
        
        # Adiciona TSC apenas se disponível
        if self.has_tsc:
            try:
                timestamp['tsc'] = self.click_sync.read_tsc()
            except:
                self.has_tsc = False
        
        self.timestamps.append(timestamp)
        
        if event_name == 'Post-Click':
            self.click_timestamps.append(timestamp)
    
    def analyze_timestamps(self):
        """Análise detalhada dos timestamps capturados."""
        if len(self.timestamps) < 2:
            return
            
        sorted_timestamps = sorted(self.timestamps, key=lambda x: x['monotonic_ns'])
        
        pre_click = [ts for ts in sorted_timestamps if 'Pre-' in ts['event']]
        post_click = [ts for ts in sorted_timestamps if 'Post-' in ts['event']]
        
        pre_deviations = self._calculate_phase_deviations(pre_click)
        post_deviations = self._calculate_phase_deviations(post_click)
        
        if len(self.click_timestamps) >= 2:
            click_deviations = self._analyze_click_precision()
            self._log_click_analysis(click_deviations)
        
        self._log_timestamp_analysis(sorted_timestamps, pre_deviations, post_deviations)
    
    def _calculate_phase_deviations(self, timestamps):
        if len(timestamps) < 2:
            return ([], [], [], [])
            
        desvios_monotonic = []
        desvios_process = []
        desvios_thread = []
        desvios_tsc = []
        
        for i in range(1, len(timestamps)):
            prev, curr = timestamps[i-1], timestamps[i]
            desvios_monotonic.append(abs(curr['monotonic_ns'] - prev['monotonic_ns']))
            desvios_process.append(abs(curr['process_time_ns'] - prev['process_time_ns']))
            desvios_thread.append(abs(curr['thread_time_ns'] - prev['thread_time_ns']))
            
            if self.has_tsc and 'tsc' in prev and 'tsc' in curr:
                desvios_tsc.append(abs(curr['tsc'] - prev['tsc']))
            
        return (desvios_monotonic, desvios_process, desvios_thread, desvios_tsc)
    
    def _analyze_click_precision(self):
        if len(self.click_timestamps) < 2:
            return None
            
        base_click = self.click_timestamps[0]
        deviations = {
            'monotonic': [],
            'process': [],
            'thread': []
        }
        
        # Adiciona TSC apenas se disponível
        if self.has_tsc:
            deviations['tsc'] = []
        
        for click in self.click_timestamps[1:]:
            deviations['monotonic'].append(click['monotonic_ns'] - base_click['monotonic_ns'])
            deviations['process'].append(click['process_time_ns'] - base_click['process_time_ns'])
            deviations['thread'].append(click['thread_time_ns'] - base_click['thread_time_ns'])
            
            if self.has_tsc and 'tsc' in click and 'tsc' in base_click:
                deviations['tsc'].append(click['tsc'] - base_click['tsc'])
            
        return deviations
    
    def _log_timestamp_analysis(self, timestamps, pre_deviations, post_deviations):
        self.logger.info("\n🔬 Análise Precisa de Timestamps:")
        
        for ts in timestamps:
            event_icon = "🎯" if "Click" in ts['event'] else "⚡"
            log_msg = (
                f"  {event_icon} {ts['event']} (Driver {ts['driver_id']}):\n"
                f"    ⏱️ Monotonic: {ts['monotonic_ns']} ns\n"
                f"    ⚙️ Process Time: {ts['process_time_ns']} ns\n"
                f"    🧵 Thread Time: {ts['thread_time_ns']} ns"
            )
            
            if self.has_tsc and 'tsc' in ts:
                log_msg += f"\n    🔄 TSC: {ts['tsc']}"
            
            self.logger.info(log_msg)
        
        self.logger.info("\n📊 Desvios Pré-Clique:")
        self._log_phase_deviations(pre_deviations)
        
        self.logger.info("\n📈 Desvios Pós-Clique:")
        self._log_phase_deviations(post_deviations)
    
    def _log_phase_deviations(self, deviations):
        if not any(deviations):
            return
            
        monotonic, process, thread, tsc = deviations
        metrics = [
            ("⏱️ Monotonic", monotonic),
            ("⚙️ Process Time", process),
            ("🧵 Thread Time", thread)
        ]
        
        if self.has_tsc and tsc:
            metrics.append(("🔄 TSC", tsc))
        
        for metric_name, desvios in metrics:
            if desvios:
                mean_dev = sum(desvios) / len(desvios)
                max_dev = max(desvios)
                self.logger.info(
                    f"  📏 Desvio {metric_name}:\n"
                    f"    📉 Médio: {mean_dev:.4f} ns\n"
                    f"    📈 Máximo: {max_dev:.4f} ns"
                )
    
    def _log_click_analysis(self, deviations):
        if not deviations:
            return
            
        self.logger.info("\n🎯 Análise de Precisão dos Cliques:")
        
        icons = {
            'monotonic': '⏱️',
            'tsc': '🔄',
            'process': '⚙️',
            'thread': '🧵'
        }
        
        for metric, values in deviations.items():
            if values:
                max_dev_us = max(map(abs, values)) / 1000
                avg_dev_us = sum(map(abs, values)) / len(values) / 1000
                
                self.logger.info(f"  {icons.get(metric, '📊')} Desvio {metric}:")
                self.logger.info(f"    🎯 Máximo: {max_dev_us:.3f}μs")
                self.logger.info(f"    🎯 Médio: {avg_dev_us:.3f}μs")
                
                if metric in ('monotonic', 'tsc') and max_dev_us > 100:
                    self.logger.warning(
                        f"  ⚠️ Desvio {metric} crítico detectado: {max_dev_us:.3f}μs"
                    )