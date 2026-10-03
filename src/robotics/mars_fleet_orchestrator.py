"""Mars Fleet Orchestrator — Orquestração de Frota Robótica Heterogênea para E2-MARCIANO.
========================================================================================
Implementa a governança, despacho dinâmico de tarefas, cinemática energética,
acúmulo de poeira e degradação mecânica para a frota de 8 tipos de robôs da Estação Árvore:
  - Rover Pesado (NASA RASSOR / ExoMars)
  - Quadrúpede (Boston Dynamics Spot / China Unitree B2)
  - Drone de Asa Fixa (Prandtl-M)
  - Drone de Rotor (Ingenuity Escalado)
  - Humanoide (Tesla Optimus / Agility Digit / Atlas)
  - Enxame de Insetos (Harvard RoboBee / Beihang MAV)
  - Serpente Robô (Carnegie Mellon / Harbin HIT Snake)
  - Escavador / Toupeira (IceBreaker / ExoMars Drill)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class RobotType(Enum):
    ROVER_HEAVY = "rover_heavy"
    QUADRUPED = "quadruped"
    DRONE_FIXED = "drone_fixed"
    DRONE_ROTARY = "drone_rotary"
    HUMANOID = "humanoid"
    INSECT = "insect"
    SNAKE = "snake"
    EXCAVATOR = "excavator"


@dataclass
class Robot:
    id: str
    type: RobotType
    battery_soc: float = 1.0  # 0.0 a 1.0
    health: float = 1.0       # 0.0 a 1.0
    location: str = "tronco"  # "tronco", "braço_01".."braço_12", "tunel_anelar", "mina_regolito"
    payload_kg: float = 10.0
    max_speed_m_s: float = 1.0
    energy_consumption_w: float = 100.0
    dust_accumulation_pct: float = 0.0  # 0.0 a 100.0%
    hours_operated: float = 0.0
    is_busy: bool = False
    assigned_task_id: Optional[str] = None


@dataclass
class FleetTask:
    task_id: str
    required_type: RobotType
    location: str
    priority: int = 2  # 1 = Crítica/Emergência, 2 = Operação/Rotina, 3 = Manutenção preventiva
    energy_required_wh: float = 200.0
    duration_hours: float = 2.0
    status: str = "PENDING"  # "PENDING", "ASSIGNED", "COMPLETED", "FAILED"
    assigned_robot_id: Optional[str] = None


class FleetOrchestrator:
    """Orquestrador autônomo central da frota heterogênea da Estação Árvore."""

    def __init__(self) -> None:
        self.fleet: List[Robot] = []
        self.tasks: List[FleetTask] = []
        self.history: List[Dict[str, Any]] = []

    def add_robot(self, robot: Robot) -> None:
        self.fleet.append(robot)

    def register_task(self, task: FleetTask) -> None:
        self.tasks.append(task)

    def allocate_task(self, task: FleetTask) -> Optional[Robot]:
        """Aloca a tarefa ao robô disponível com melhor pontuação multivariada."""
        available = [
            r for r in self.fleet
            if not r.is_busy and r.battery_soc >= 0.20 and r.health >= 0.40
        ]
        if not available:
            return None

        scored_robots = []
        for robot in available:
            # 1. Correspondência de tipo (peso 3.0 se exato)
            type_score = 3.0 if robot.type == task.required_type else 0.5

            # 2. Proximidade de localização (peso 1.5 se já estiver no local)
            loc_score = 1.5 if robot.location == task.location else 0.5

            # 3. Estado de carga e saúde física (peso 2.0)
            soc_score = robot.battery_soc * 1.5
            health_score = robot.health * 1.5

            # 4. Penalidade por poeira eletrostática nos atuadores/sensores
            dust_penalty = (robot.dust_accumulation_pct / 100.0) * 0.8

            total_score = type_score + loc_score + soc_score + health_score - dust_penalty
            scored_robots.append((total_score, robot))

        scored_robots.sort(key=lambda x: x[0], reverse=True)
        best_robot = scored_robots[0][1]

        # Vincular
        best_robot.is_busy = True
        best_robot.assigned_task_id = task.task_id
        task.status = "ASSIGNED"
        task.assigned_robot_id = best_robot.id

        return best_robot

    def step(
        self,
        dt_hours: float = 1.0,
        environmental_dust_flux: float = 0.01,
        wind_speed_m_s: float = 8.0
    ) -> Dict[str, Any]:
        """Avança o relógio da frota por dt_hours, calculando desgaste, descarga e recarga."""
        tasks_completed = 0
        tasks_failed = 0

        # 1. Despachar tarefas pendentes antes do avanço temporal
        pending = [t for t in self.tasks if t.status == "PENDING"]
        for p in pending:
            self.allocate_task(p)

        for robot in self.fleet:
            # Acúmulo de poeira externa em Marte
            dust_inc = environmental_dust_flux * (wind_speed_m_s / 5.0) * dt_hours
            robot.dust_accumulation_pct = min(100.0, robot.dust_accumulation_pct + dust_inc)

            if robot.is_busy and robot.assigned_task_id:
                task = next((t for t in self.tasks if t.task_id == robot.assigned_task_id), None)
                if task:
                    # Consumo de bateria
                    wh_consumed = robot.energy_consumption_w * dt_hours
                    battery_capacity_wh = 1000.0  # nominal
                    delta_soc = wh_consumed / battery_capacity_wh
                    robot.battery_soc = max(0.0, robot.battery_soc - delta_soc)

                    # Desgaste mecânico (maior se poeira e vento altos)
                    wear_factor = 0.0005 * (1.0 + robot.dust_accumulation_pct / 50.0) * dt_hours
                    robot.health = max(0.0, robot.health - wear_factor)
                    robot.hours_operated += dt_hours

                    # Verificar conclusão ou falha por esgotamento de energia
                    if robot.battery_soc <= 0.05:
                        robot.is_busy = False
                        robot.assigned_task_id = None
                        task.status = "FAILED"
                        tasks_failed += 1
                    elif robot.hours_operated >= task.duration_hours:
                        robot.is_busy = False
                        robot.assigned_task_id = None
                        task.status = "COMPLETED"
                        tasks_completed += 1
            else:
                # Robô ocioso em estação de recarga / doca
                # Recarga solar / nuclear a 25% por hora
                robot.battery_soc = min(1.0, robot.battery_soc + 0.25 * dt_hours)
                # Limpeza automática de poeira por sopradores EDS na base
                if robot.location in ["tronco", "braço_01", "braço_02", "braço_03"]:
                    robot.dust_accumulation_pct = max(0.0, robot.dust_accumulation_pct - 5.0 * dt_hours)

        # Métricas de prontidão
        operational_count = sum(1 for r in self.fleet if r.health > 0.5 and r.battery_soc > 0.2)
        readiness_pct = (operational_count / max(1, len(self.fleet))) * 100.0

        return {
            "total_fleet": len(self.fleet),
            "operational_robots": operational_count,
            "readiness_pct": round(readiness_pct, 2),
            "tasks_completed": tasks_completed,
            "tasks_failed": tasks_failed,
        }

    def simulate_fleet_health(
        self,
        sols: int = 10,
        avg_dust: float = 0.015,
        avg_wind: float = 9.0
    ) -> Dict[str, Any]:
        """Simula a sobrevivência e prontidão da frota ao longo de múltiplos sols."""
        total_hours = sols * 24.66
        step_dt = 1.0
        steps = int(total_hours / step_dt)

        for _ in range(steps):
            self.step(dt_hours=step_dt, environmental_dust_flux=avg_dust, wind_speed_m_s=avg_wind)

        # Sumário por tipo
        type_summary: Dict[str, Dict[str, float]] = {}
        for r_type in RobotType:
            type_robots = [r for r in self.fleet if r.type == r_type]
            if type_robots:
                avg_h = sum(r.health for r in type_robots) / len(type_robots)
                avg_b = sum(r.battery_soc for r in type_robots) / len(type_robots)
                avg_dust_acc = sum(r.dust_accumulation_pct for r in type_robots) / len(type_robots)
                type_summary[r_type.value] = {
                    "count": len(type_robots),
                    "mean_health": round(avg_h, 3),
                    "mean_soc": round(avg_b, 3),
                    "mean_dust_pct": round(avg_dust_acc, 2),
                }

        return {
            "sols_simulated": sols,
            "final_fleet_size": len(self.fleet),
            "type_breakdown": type_summary,
            "overall_health": round(sum(r.health for r in self.fleet) / max(1, len(self.fleet)), 3),
        }

    def init_phase1_fleet(self) -> None:
        """Inicializa a frota da Fase 1 (Sínodos 0-3, ~6 anos, 74 robôs)."""
        self.fleet.clear()
        # 4 Rovers pesados
        for i in range(4):
            self.add_robot(Robot(f"rover_{i:02d}", RobotType.ROVER_HEAVY, payload_kg=500.0, max_speed_m_s=0.5, energy_consumption_w=200.0))
        # 8 Quadrúpedes
        for i in range(8):
            self.add_robot(Robot(f"quad_{i:02d}", RobotType.QUADRUPED, payload_kg=120.0, max_speed_m_s=2.0, energy_consumption_w=150.0))
        # 6 Drones asa fixa
        for i in range(6):
            self.add_robot(Robot(f"drone_fix_{i:02d}", RobotType.DRONE_FIXED, payload_kg=5.0, max_speed_m_s=15.0, energy_consumption_w=180.0))
        # 4 Humanoides
        for i in range(4):
            self.add_robot(Robot(f"humanoid_{i:02d}", RobotType.HUMANOID, payload_kg=35.0, max_speed_m_s=1.2, energy_consumption_w=250.0))
        # 50 Insetos
        for i in range(50):
            self.add_robot(Robot(f"insect_{i:02d}", RobotType.INSECT, payload_kg=0.01, max_speed_m_s=3.0, energy_consumption_w=5.0))
        # 2 Escavadores
        for i in range(2):
            self.add_robot(Robot(f"excavator_{i:02d}", RobotType.EXCAVATOR, payload_kg=200.0, max_speed_m_s=0.2, energy_consumption_w=350.0))

    def init_phase3_fleet(self) -> None:
        """Inicializa a frota da Fase 3 (Sínodos 11-27, ~60 anos, 727 robôs)."""
        self.fleet.clear()
        configs = [
            (RobotType.ROVER_HEAVY, 30, 500.0, 0.5, 200.0),
            (RobotType.QUADRUPED, 50, 120.0, 2.0, 150.0),
            (RobotType.DRONE_FIXED, 40, 5.0, 15.0, 180.0),
            (RobotType.DRONE_ROTARY, 30, 3.0, 8.0, 220.0),
            (RobotType.HUMANOID, 40, 35.0, 1.2, 250.0),
            (RobotType.INSECT, 500, 0.01, 3.0, 5.0),
            (RobotType.SNAKE, 20, 15.0, 0.8, 80.0),
            (RobotType.EXCAVATOR, 15, 200.0, 0.2, 350.0),
            (RobotType.HUMANOID, 2, 50.0, 1.0, 200.0),  # Submarino/Adaptado
        ]
        count = 0
        for r_type, qty, payload, speed, power in configs:
            for j in range(qty):
                count += 1
                self.add_robot(Robot(
                    id=f"{r_type.value}_{j:03d}",
                    type=r_type,
                    payload_kg=payload,
                    max_speed_m_s=speed,
                    energy_consumption_w=power
                ))
