"""Mars Surface Organ — a pele multicamada que come tempestade.

Decisão de design (2026-10-03): coexistir com o ambiente em vez de
blindar contra ele — o calor residual do corpo e a carga eletrostática
da própria poeira viram ferramentas de defesa.

Stack físico (avaliação da proposta + correções de stack):
  pele composta   — radiador de alta emissividade COM eletrodos EDS
                    interdigitados sob polimida fina (mesma camada —
                    eletrodo sob alumínio não alcança o grão).
                    EDS dispara por EVENTO (sensor capacitivo detecta
                    acúmulo), não contínuo — menos energia, menos EMI
                    (o próprio EDS é fonte de EMI; GND na stack).
  coletor         — geometria (defletor/ciclone) captura o ejetado;
                    sem ele o EDS só redeposita a poeira ao lado.
  anel quente     — guarda termoforético em bordas/aberturas
                    (gimbals, airlock, conectores) — regime mm-cm onde
                    termoforese domina. +50-70C via calor roteado.
  forno dedicado  — sinterização por micro-ondas (Shulman/NASA):
                    poeira coletada vira bloco de blindagem.

Ancoras de literatura:
  Pathfinder MAE: obscurecimento de painel ~0.28%/dia (Calle et al.,
  NASA TM 2012-2164) — sem tempestade global.
  Micro-ondas em simulante: ~2.5 kWh/kg sinterizado (FOM 1.8-2.9).
  Regolito ~1600 kg/m3: 1 mm/m2 = 1.6 kg de blindagem equivalente.

O laço honesto: poeira chega -> EDS ejeta (custa Wh, degrada eletrodo)
-> coletor captura fração -> forno sinteriza (custa kWh) -> bloco
engrossa blindagem -> menos dose. O residual NAO ejetado continua
alimentando wear — o orgão reduz dano, não decreta fim da poeira.

Expectativas calibradas (validação 5000 sols, 3 tempestades, 50 m²):
  - Integridade do corpo ~0.55 mesmo com órgão: reflete o orçamento
    de reparo (repair_fraction=0.12 do labor), não a física do órgão.
    Subir repair_fraction ou priorizar camadas críticas eleva a
    integridade sem mudar nada aqui.
  - Blindagem sinterizada é INCREMENTO, não primária: ~0.4 µm/sol
    (~8 mm em 60 anos). Serve como camada sacrificável/fouling-sink;
    blindagem primária contra GCR continua sendo regolito escavado
    ou água em escala de metro — nunca esperar "metros de graça".

PassiveBerm (v2, 2026-10-03) — cerca de areia passiva a barlavento:
  intercepta a componente SALTANTE do fluxo (grãos ~80-200 µm rasando o
  solo) — não a poeira fina suspensa, que a atravessa. Cresce durante
  tempestades (sand-fence: vento desacelera -> carga deposita no berm)
  e decai em calmaria (reptação + slump). Não é barreira absoluta: cap
  ~60% de interceptação da fração saltante; altura útil 0-3 m. Custo:
  apenas escavação inicial (horas de dozer, se houver) — depois o
  ambiente a mantém parcialmente. É a defesa "de graça" que o próprio
  vento constrói, no espírito do órgão (coexistir, não blindar).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class PassiveBerm:
    """Cerca de areia passiva a barlavento do órgão de superfície.

    Física: o berm intercepta a fração SALTANTE do transporte eólico
    (grãos em saltação ~80-200 µm, trajetórias a cm do solo); a poeira
    fina em suspensão o atravessa. Em tempestade ele cresce (sand-fence:
    desaceleração deposita carga no berm); em calmaria decai por
    reptação/slump. Interceptação capada — nunca é blindagem total.
    """

    height_m: float = 0.4                 # cota inicial (escavação rápida)
    max_height_m: float = 3.0
    saltation_frac_of_flux: float = 0.5   # fração do fluxo que vem saltando
    intercept_cap: float = 0.6            # teto físico de interceptação
    grow_per_flux: float = 0.0025         # m por (dust_flux × vento) — tempestade alimenta
    erode_per_sol: float = 0.0004         # m/sol em calmaria — reptação + slump
    wind_threshold_ms: float = 5.0        # abaixo disso quase nada salta

    def step_sol(self, env: Dict[str, float]) -> Dict[str, float]:
        dust_flux = env.get("dust_flux", 1.0)
        wind_ms = env.get("wind_speed_ms", 0.0)

        # crescimento: evento de saltação deposita carga no berm
        driving = dust_flux * max(0.0, wind_ms - self.wind_threshold_ms)
        if driving > 0:
            self.height_m = min(self.max_height_m,
                                self.height_m + self.grow_per_flux * driving)
        else:
            self.height_m = max(0.05, self.height_m - self.erode_per_sol)

        # interceptação efetiva: sobe com altura até o cap, só sobre a
        # fração saltante do fluxo, e some se o vento mal alcança a base
        height_eff = min(1.0, self.height_m / 1.5)          # 1.5 m ~ eficaz
        wind_eff = min(1.0, wind_ms / 15.0) if wind_ms > 0 else 0.0
        frac = (self.intercept_cap * self.saltation_frac_of_flux
                * height_eff * wind_eff)
        return {
            "berm_height_m": round(self.height_m, 4),
            "berm_intercept_frac": round(frac, 4),
            "berm_driving": round(driving, 3),
        }


@dataclass
class SurfaceOrgan:
    """Pele + anel + coletor + forno. Um órgão do StationBody."""

    # --- parâmetros de design (calibráveis; âncoras no docstring) ---
    capture_area_m2: float = 50.0         # área exposta tratada pelo órgão
    deposit_kg_m2_sol: float = 3e-5       # ~0.28%/dia Pathfinder -> ~3 µg/cm2/sol
    eds_energy_wh: float = 0.8            # Wh por disparo de ejeção
    capture_fraction: float = 0.35        # fração do ejetado que o coletor pega
    sinter_kwh_per_kg: float = 2.5        # micro-ondas em simulante (medido)
    block_kg_per_mm_shield: float = 1.6   # 1 mm/m2 a 1600 kg/m3
    eds_fatigue_pulse: float = 2e-6       # desgaste do eletrodo por disparo
    eds_fatigue_thermal: float = 8e-7     # fadiga extra por ciclo térmico sol
    eds_min_health: float = 0.3           # abaixo disso o EDS para de disparar
    eject_efficiency: float = 0.85        # fração do depositado que sai por pulso
    fouling_wear_gain: float = 1e-5       # kg residual -> wear extra/sol
    sinter_batch_kg: float = 5.0          # tamanho do lote da câmara
    sinter_min_batch_kg: float = 0.25     # micro-ondas sinteriza em sub-kg
    shielding_rad_gain: float = 50.0      # fator = 1/(1+shielding_m*gain)
    berm: PassiveBerm = field(default_factory=PassiveBerm)

    # --- estado ---
    dust_captured_kg: float = 0.0
    eds_cycles: int = 0
    sintered_mass_kg: float = 0.0
    shielding_m: float = 0.0              # acima do regolito escavado primário
    eds_health: float = 1.0
    _pending_capture_kg: float = 0.0      # buffer aguardando lote de forno

    def step_sol(self, env: Dict[str, float], latent: float,
                 rng: random.Random) -> Dict[str, float]:
        """Um sol do órgão: deposita, ejeta (se houver margem), captura,
        sinteriza. Lê power_margin do env (default 0.6 — margem moderada)."""
        dust_flux = env.get("dust_flux", 1.0)
        dt_ground = env.get("ground_temp_delta", 60.0)
        wind_ms = env.get("wind_speed_ms", 0.0)
        power_margin = env.get("power_margin", 0.6)

        # orçamento energético diário do órgão: power_margin é fração de
        # uma potência base P_base × 24h -> kWh/dia. P_base vem do env
        # (power_base_kw — o sim injeta 100 kWe do reator de fissão);
        # ausente = 1 kW (retrocompatível).
        # EDS e forno disputam o MESMO orçamento — energia não é de graça.
        energy_budget_kwh = power_margin * 24.0 * env.get("power_base_kw", 1.0)
        energy_used_kwh = 0.0

        # berm primeiro: intercepta a fração saltante antes da pele
        berm_res = self.berm.step_sol(env)

        # deposição do sol — Pathfinder MAE: ~0.28%/dia de obscurecimento
        # (~3 µg/cm²/sol em calma), escalado pela área exposta tratada
        deposited_kg = (self.deposit_kg_m2_sol * self.capture_area_m2
                        * dust_flux * (1.0 + 0.5 * min(3.0, wind_ms / 10.0)))
        deposited_kg *= (1.0 - berm_res["berm_intercept_frac"])

        # EDS disparado por acúmulo — duty-cycle baixo por design
        eds_fired = 0
        eds_cost_kwh = self.eds_energy_wh / 1000.0
        if (dust_flux > 0.8 and power_margin > 0.2
                and self.eds_health > self.eds_min_health
                and energy_used_kwh + eds_cost_kwh <= energy_budget_kwh):
            eds_fired = 1
            energy_used_kwh += eds_cost_kwh
            self.eds_cycles += 1
            self.eds_health = max(
                0.0, self.eds_health - self.eds_fatigue_pulse
                - self.eds_fatigue_thermal * (dt_ground / 60.0))

        ejected_kg = deposited_kg * (self.eject_efficiency * self.eds_health
                                     if eds_fired else 0.0)
        captured_kg = ejected_kg * self.capture_fraction
        self._pending_capture_kg += captured_kg
        self.dust_captured_kg += captured_kg
        residual_kg = deposited_kg - ejected_kg     # fica na pele: fouling real

        # sinterização em lote — débito real do mesmo orçamento
        sintered_kg = 0.0
        if (self._pending_capture_kg >= self.sinter_min_batch_kg
                and power_margin > 0.5):
            batch = min(self._pending_capture_kg, self.sinter_batch_kg)
            sinter_cost_kwh = batch * self.sinter_kwh_per_kg
            if energy_used_kwh + sinter_cost_kwh <= energy_budget_kwh:
                energy_used_kwh += sinter_cost_kwh
                self._pending_capture_kg -= batch
                self.sintered_mass_kg += batch
                sintered_kg = batch
                self.shielding_m += (batch / self.block_kg_per_mm_shield
                                     / 1000.0)

        return {
            "organ_deposited_kg": round(deposited_kg, 6),
            "organ_ejected_kg": round(ejected_kg, 6),
            "organ_captured_kg": round(captured_kg, 6),
            "organ_sintered_kg": round(sintered_kg, 6),
            "organ_residual_fouling_kg": round(residual_kg, 6),
            "organ_eds_fired": eds_fired,
            "organ_eds_cycles": self.eds_cycles,
            "organ_eds_health": round(self.eds_health, 5),
            "organ_dust_captured_kg": round(self.dust_captured_kg, 4),
            "organ_sintered_mass_kg": round(self.sintered_mass_kg, 4),
            "organ_shielding_m": round(self.shielding_m, 6),
            "berm_height_m": berm_res["berm_height_m"],
            "berm_intercept_frac": berm_res["berm_intercept_frac"],
            "organ_energy_used_kwh": round(energy_used_kwh, 6),
            "organ_energy_budget_kwh": round(energy_budget_kwh, 4),
        }

    def neutrosophic(self) -> Dict[str, float]:
        """Saúde composta: eletrodo + capacidade produtiva (forno/blindagem).

        Um órgão com EDS são mas forno morto não é T=1.0 — compõe os três
        subsistemas pesando o que cada um representa da função do órgão."""
        t = (0.5 * self.eds_health
             + 0.3 * min(1.0, self.sintered_mass_kg / 10.0)
             + 0.2 * min(1.0, self.shielding_m / 0.01))
        return {"T": round(t, 4), "I": 0.05, "F": round(1.0 - t, 4)}
