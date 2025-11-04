import json
import os
import time
from datetime import datetime


class PontoManager:
    """Classe responsável pelo gerenciamento de pontos"""
    
    def __init__(self, pontos_file="pontos_registrados.json"):
        self.pontos_file = pontos_file
        self.recognition_sessions = {}  # Armazena sessões de reconhecimento contínuo
        self.recognition_cooldown = {}  # Cooldown entre registros
        self.RECOGNITION_TIME_REQUIRED = 3.0  # 3 segundos de reconhecimento contínuo
        self.COOLDOWN_TIME = 30.0  # 30 segundos entre registros
    
    def start_recognition_session(self, nome):
        """Inicia uma sessão de reconhecimento para uma pessoa"""
        current_time = time.time()
        
        if nome not in self.recognition_sessions:
            self.recognition_sessions[nome] = {
                'start_time': current_time,
                'last_seen': current_time,
                'continuous': True
            }
            return False, 0.0  # Não registra ainda, acabou de começar
        
        session = self.recognition_sessions[nome]
        
        # Verifica se o reconhecimento foi contínuo
        if current_time - session['last_seen'] > 1.0:  # Mais de 1 segundo sem ver
            # Reinicia a sessão
            session['start_time'] = current_time
            session['last_seen'] = current_time
            session['continuous'] = True
            return False, 0.0
        
        # Atualiza último momento visto
        session['last_seen'] = current_time
        
        # Calcula tempo de reconhecimento contínuo
        recognition_time = current_time - session['start_time']
        
        # Verifica se atingiu o tempo necessário
        if recognition_time >= self.RECOGNITION_TIME_REQUIRED:
            if self.can_register_point(nome):
                success = self.register_point(nome)
                if success:
                    # Remove a sessão após registrar
                    del self.recognition_sessions[nome]
                    return True, recognition_time
            
            # Se não pode registrar por cooldown, remove a sessão
            del self.recognition_sessions[nome]
            return False, recognition_time
        
        return False, recognition_time
    
    def can_register_point(self, nome):
        """Verifica se pode registrar ponto (cooldown)"""
        current_time = time.time()
        
        if nome in self.recognition_cooldown:
            if current_time - self.recognition_cooldown[nome] < self.COOLDOWN_TIME:
                return False
        
        return True
    
    def get_cooldown_remaining(self, nome):
        """Retorna tempo restante de cooldown em segundos"""
        if nome not in self.recognition_cooldown:
            return 0
        
        current_time = time.time()
        elapsed = current_time - self.recognition_cooldown[nome]
        remaining = max(0, self.COOLDOWN_TIME - elapsed)
        
        return remaining
    
    def register_point(self, nome):
        """Registra o ponto de uma pessoa"""
        now = datetime.now()
        horario = now.strftime("%Y-%m-%d %H:%M:%S")
        
        # Atualiza cooldown
        self.recognition_cooldown[nome] = time.time()
        
        # Carrega pontos existentes
        pontos = self.load_pontos()
        
        # Adiciona novo ponto
        ponto = {
            "nome": nome,
            "horario": horario,
            "data": now.strftime("%Y-%m-%d"),
            "hora": now.strftime("%H:%M:%S"),
            "timestamp": time.time()
        }
        pontos.append(ponto)
        
        # Salva pontos
        success = self.save_pontos(pontos)
        
        if success:
            print(f"PONTO REGISTRADO: {nome} - {horario}")
            return ponto
        
        return None
    
    def load_pontos(self):
        """Carrega pontos do arquivo"""
        if not os.path.exists(self.pontos_file):
            return []
        
        try:
            with open(self.pontos_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    
    def save_pontos(self, pontos):
        """Salva pontos no arquivo"""
        try:
            with open(self.pontos_file, 'w', encoding='utf-8') as f:
                json.dump(pontos, f, ensure_ascii=False, indent=2)
            return True
        except IOError:
            return False
    
    def get_pontos_today(self):
        """Retorna pontos do dia atual"""
        pontos = self.load_pontos()
        today = datetime.now().strftime("%Y-%m-%d")
        
        pontos_hoje = [p for p in pontos if p.get("data") == today]
        return sorted(pontos_hoje, key=lambda x: x["horario"], reverse=True)
    
    def get_pontos_by_date(self, data):
        """Retorna pontos de uma data específica"""
        pontos = self.load_pontos()
        pontos_data = [p for p in pontos if p.get("data") == data]
        return sorted(pontos_data, key=lambda x: x["horario"], reverse=True)
    
    def get_pontos_by_person(self, nome, limit=None):
        """Retorna pontos de uma pessoa específica"""
        pontos = self.load_pontos()
        pontos_pessoa = [p for p in pontos if p.get("nome") == nome]
        pontos_pessoa = sorted(pontos_pessoa, key=lambda x: x["horario"], reverse=True)
        
        if limit:
            return pontos_pessoa[:limit]
        
        return pontos_pessoa
    
    def get_statistics_today(self):
        """Retorna estatísticas do dia"""
        pontos_hoje = self.get_pontos_today()
        
        total_pontos = len(pontos_hoje)
        pessoas_diferentes = len(set(p["nome"] for p in pontos_hoje))
        
        ultimo_ponto = None
        if pontos_hoje:
            ultimo_ponto = pontos_hoje[0]["hora"]
        
        return {
            "total_pontos": total_pontos,
            "pessoas_diferentes": pessoas_diferentes,
            "ultimo_ponto": ultimo_ponto,
            "pontos": pontos_hoje
        }
    
    def cleanup_old_sessions(self, max_age=10.0):
        """Remove sessões antigas (mais de 10 segundos sem atualização)"""
        current_time = time.time()
        to_remove = []
        
        for nome, session in self.recognition_sessions.items():
            if current_time - session['last_seen'] > max_age:
                to_remove.append(nome)
        
        for nome in to_remove:
            del self.recognition_sessions[nome]
    
    def get_active_sessions(self):
        """Retorna informações sobre sessões ativas"""
        current_time = time.time()
        active_sessions = {}
        
        for nome, session in self.recognition_sessions.items():
            recognition_time = current_time - session['start_time']
            time_remaining = max(0, self.RECOGNITION_TIME_REQUIRED - recognition_time)
            
            active_sessions[nome] = {
                "recognition_time": recognition_time,
                "time_remaining": time_remaining,
                "progress": min(1.0, recognition_time / self.RECOGNITION_TIME_REQUIRED)
            }
        
        return active_sessions