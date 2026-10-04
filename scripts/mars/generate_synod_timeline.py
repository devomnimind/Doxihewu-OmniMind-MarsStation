import sys
import subprocess
import os

def build_svg():
    w = 2560
    h = 1440
    
    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" font-family="system-ui, -apple-system, Segoe UI, Roboto, Helvetica, sans-serif">')
    
    # Defs
    svg.append('''<defs>
    <!-- Gradients -->
    <linearGradient id="bgSky" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#0b0d14"/>
      <stop offset="35%" stop-color="#141722"/>
      <stop offset="65%" stop-color="#2a1a1c"/>
      <stop offset="100%" stop-color="#4d2417"/>
    </linearGradient>

    <linearGradient id="groundGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#803318"/>
      <stop offset="25%" stop-color="#5e2410"/>
      <stop offset="70%" stop-color="#36150a"/>
      <stop offset="100%" stop-color="#1b0a05"/>
    </linearGradient>

    <radialGradient id="haloGrad" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#1c472d" stop-opacity="0.95"/>
      <stop offset="35%" stop-color="#22422a" stop-opacity="0.85"/>
      <stop offset="65%" stop-color="#4a3622" stop-opacity="0.6"/>
      <stop offset="90%" stop-color="#732f17" stop-opacity="0.3"/>
      <stop offset="100%" stop-color="#803318" stop-opacity="0.0"/>
    </radialGradient>

    <radialGradient id="domeGlow" cx="50%" cy="35%" r="65%">
      <stop offset="0%" stop-color="#4ade80" stop-opacity="0.9"/>
      <stop offset="30%" stop-color="#10b981" stop-opacity="0.75"/>
      <stop offset="70%" stop-color="#065f46" stop-opacity="0.5"/>
      <stop offset="100%" stop-color="#022c22" stop-opacity="0.15"/>
    </radialGradient>

    <linearGradient id="solarGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1e3a8a"/>
      <stop offset="50%" stop-color="#0284c7"/>
      <stop offset="100%" stop-color="#0f172a"/>
    </linearGradient>

    <linearGradient id="trunkGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#334155"/>
      <stop offset="30%" stop-color="#64748b"/>
      <stop offset="70%" stop-color="#475569"/>
      <stop offset="100%" stop-color="#1e293b"/>
    </linearGradient>

    <linearGradient id="spineGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#38bdf8"/>
      <stop offset="30%" stop-color="#94a3b8"/>
      <stop offset="55%" stop-color="#f59e0b"/>
      <stop offset="80%" stop-color="#10b981"/>
      <stop offset="100%" stop-color="#34d399"/>
    </linearGradient>

    <!-- Filters -->
    <filter id="glowGreen" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="7" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>

    <filter id="glowGold" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="5" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>

    <!-- Grid Patterns -->
    <pattern id="techGrid" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#475569" stroke-width="0.5" stroke-opacity="0.15"/>
    </pattern>

    <pattern id="solarGrid" width="8" height="6" patternUnits="userSpaceOnUse">
      <rect width="8" height="6" fill="#0369a1" stroke="#38bdf8" stroke-width="0.4"/>
    </pattern>

    <pattern id="brickPattern" width="12" height="6" patternUnits="userSpaceOnUse">
      <rect width="12" height="6" fill="#78350f" stroke="#451a03" stroke-width="0.5"/>
      <path d="M 0 3 L 12 3 M 6 0 L 6 3 M 0 6 L 12 6 M 6 3 L 6 6" stroke="#451a03" stroke-width="0.5"/>
    </pattern>
  </defs>''')

    # Background Sky
    svg.append(f'<rect width="{w}" height="{h}" fill="url(#bgSky)"/>')
    svg.append(f'<rect width="{w}" height="{h}" fill="url(#techGrid)"/>')

    # Stars & Moons
    svg.append('''<g opacity="0.4">
      <circle cx="210" cy="95" r="1.2" fill="#ffffff"/>
      <circle cx="450" cy="140" r="0.9" fill="#94a3b8"/>
      <circle cx="890" cy="70" r="1.5" fill="#f8fafc"/>
      <circle cx="1120" cy="120" r="1.1" fill="#cbd5e1"/>
      <circle cx="1540" cy="85" r="1.4" fill="#ffffff"/>
      <circle cx="1780" cy="150" r="0.8" fill="#94a3b8"/>
      <circle cx="2210" cy="110" r="1.3" fill="#ffffff"/>
      <circle cx="2420" cy="75" r="1.0" fill="#e2e8f0"/>
      <!-- Deimos / Phobos -->
      <ellipse cx="2360" cy="130" rx="3.5" ry="2.2" fill="#cbd5e1" opacity="0.7"/>
    </g>''')

    # Top Header Banner
    svg.append('''<g id="header">
      <line x1="60" y1="45" x2="2500" y2="45" stroke="#475569" stroke-width="1" stroke-opacity="0.6"/>
      <line x1="60" y1="48" x2="2500" y2="48" stroke="#334155" stroke-width="0.5" stroke-opacity="0.4"/>
      
      <path d="M 60 55 L 60 45 L 80 45" fill="none" stroke="#38bdf8" stroke-width="2"/>
      <path d="M 2500 55 L 2500 45 L 2480 45" fill="none" stroke="#38bdf8" stroke-width="2"/>

      <text x="65" y="32" fill="#38bdf8" font-size="12" font-family="monospace" letter-spacing="3">SYSTEM ONTOGENY // CANONICAL TIMELINE</text>
      <text x="65" y="80" fill="#f8fafc" font-size="28" font-weight="800" letter-spacing="1">DOXIHEWU-OMNIMIND MARS STATION</text>
      <text x="680" y="80" fill="#94a3b8" font-size="22" font-weight="300" letter-spacing="0.5">// 27-SYNOD MACRO-EVOLUTION (21,060 SOLS)</text>

      <!-- Badges -->
      <g transform="translate(1620, 60)" font-family="monospace" font-size="10">
        <rect x="0" y="0" width="130" height="24" rx="3" fill="#1e293b" stroke="#475569" stroke-width="0.8"/>
        <text x="65" y="16" fill="#38bdf8" text-anchor="middle">v19-SOILWASH [SIM]</text>

        <rect x="140" y="0" width="100" height="24" rx="3" fill="#1e293b" stroke="#475569" stroke-width="0.8"/>
        <text x="190" y="16" fill="#f59e0b" text-anchor="middle">SEED: 42</text>

        <rect x="250" y="0" width="140" height="24" rx="3" fill="#1e293b" stroke="#475569" stroke-width="0.8"/>
        <text x="320" y="16" fill="#10b981" text-anchor="middle">POOL: 100 kWe FISS</text>

        <rect x="400" y="0" width="170" height="24" rx="3" fill="#1e293b" stroke="#475569" stroke-width="0.8"/>
        <text x="485" y="16" fill="#cbd5e1" text-anchor="middle">TOPOLOGY: 12-ARM RADIAL</text>

        <rect x="580" y="0" width="150" height="24" rx="3" fill="#1e293b" stroke="#475569" stroke-width="0.8"/>
        <text x="655" y="16" fill="#94a3b8" text-anchor="middle">TOTAL: 21,060 SOLS</text>
      </g>
    </g>''')

    # Main Horizon and Ground Terrain
    svg.append('''<g id="terrain">
      <path d="M 0 760 Q 320 730 640 755 T 1280 740 T 1920 750 T 2560 745 L 2560 1120 L 0 1120 Z" fill="#4d1f11" opacity="0.6"/>
      <path d="M 0 780 Q 400 765 800 778 T 1600 770 T 2560 775 L 2560 1120 L 0 1120 Z" fill="#6a2813" opacity="0.8"/>
      <rect x="0" y="790" width="2560" height="330" fill="url(#groundGrad)"/>

      <ellipse cx="280" cy="850" rx="90" ry="18" fill="#42180a" opacity="0.6" stroke="#2c0f05" stroke-width="1"/>
      <ellipse cx="490" cy="910" rx="60" ry="12" fill="#42180a" opacity="0.5"/>
      <ellipse cx="980" cy="880" rx="130" ry="22" fill="#4a1a0c" opacity="0.5"/>
      <ellipse cx="1480" cy="860" rx="80" ry="16" fill="#4a1a0c" opacity="0.5"/>

      <g stroke="#94a3b8" stroke-width="0.5" opacity="0.3">
        <line x1="100" y1="785" x2="100" y2="795"/>
        <line x1="300" y1="785" x2="300" y2="795"/>
        <line x1="500" y1="785" x2="500" y2="795"/>
        <line x1="700" y1="785" x2="700" y2="795"/>
        <line x1="900" y1="785" x2="900" y2="795"/>
        <line x1="1100" y1="785" x2="1100" y2="795"/>
        <line x1="1300" y1="785" x2="1300" y2="795"/>
        <line x1="1500" y1="785" x2="1500" y2="795"/>
        <line x1="1700" y1="785" x2="1700" y2="795"/>
        <line x1="1900" y1="785" x2="1900" y2="795"/>
        <line x1="2100" y1="785" x2="2100" y2="795"/>
        <line x1="2300" y1="785" x2="2300" y2="795"/>
        <line x1="2500" y1="785" x2="2500" y2="795"/>
      </g>
    </g>''')

    # Era Division Backdrop Columns
    svg.append('''<g id="eraDividers">
      <line x1="665" y1="115" x2="665" y2="1080" stroke="#475569" stroke-width="1" stroke-dasharray="4 6" stroke-opacity="0.3"/>
      <line x1="1275" y1="115" x2="1275" y2="1080" stroke="#475569" stroke-width="1" stroke-dasharray="4 6" stroke-opacity="0.3"/>
      <line x1="1895" y1="115" x2="1895" y2="1080" stroke="#475569" stroke-width="1" stroke-dasharray="4 6" stroke-opacity="0.3"/>
    </g>''')

    # =========================================================================
    # ERA I: ANCHORAGE
    # =========================================================================
    svg.append('''<g id="era1_anchorage">
      <!-- Era Label Header -->
      <g transform="translate(100, 130)">
        <rect x="0" y="0" width="530" height="60" rx="4" fill="#111827" stroke="#374151" stroke-width="1" fill-opacity="0.8"/>
        <path d="M 0 0 L 0 60" stroke="#38bdf8" stroke-width="4"/>
        <text x="18" y="25" fill="#38bdf8" font-size="11" font-family="monospace" letter-spacing="2">ERA I : ANCHORAGE</text>
        <text x="18" y="47" fill="#f8fafc" font-size="18" font-weight="700">DESCENT &amp; SEEDING</text>
        <text x="350" y="36" fill="#94a3b8" font-size="12" font-family="monospace">SYNODS 0 – 3</text>
        <text x="350" y="50" fill="#64748b" font-size="11" font-family="monospace">SOLS 0 – 2,340</text>
      </g>

      <!-- Berm & Pad -->
      <ellipse cx="360" cy="790" rx="140" ry="24" fill="#381509" stroke="#54210e" stroke-width="1.5"/>

      <!-- Small Hexagonal Descent Lander -->
      <path d="M 310 740 L 260 790 M 250 790 L 270 790" stroke="#94a3b8" stroke-width="3" stroke-linecap="round"/>
      <path d="M 410 740 L 460 790 M 450 790 L 470 790" stroke="#94a3b8" stroke-width="3" stroke-linecap="round"/>
      <path d="M 335 745 L 320 795 M 310 795 L 330 795" stroke="#64748b" stroke-width="2.5" stroke-linecap="round"/>
      <path d="M 385 745 L 400 795 M 390 795 L 410 795" stroke="#64748b" stroke-width="2.5" stroke-linecap="round"/>
      
      <polygon points="310,740 410,740 430,680 390,630 330,630 290,680" fill="#475569" stroke="#cbd5e1" stroke-width="1.5"/>
      <polygon points="325,735 395,735 410,685 380,645 340,645 310,685" fill="#334155" stroke="#64748b" stroke-width="1"/>
      <path d="M 335 630 Q 360 595 385 630 Z" fill="#64748b" stroke="#e2e8f0" stroke-width="1.5"/>
      
      <circle cx="360" cy="680" r="12" fill="#0f172a" stroke="#38bdf8" stroke-width="1.5"/>
      <circle cx="360" cy="680" r="7" fill="#0284c7" opacity="0.7"/>
      
      <line x1="360" y1="595" x2="360" y2="565" stroke="#cbd5e1" stroke-width="1.5"/>
      <path d="M 345 565 Q 360 550 375 565" fill="none" stroke="#f8fafc" stroke-width="2"/>
      <circle cx="360" cy="558" r="2" fill="#38bdf8"/>

      <!-- Deployable Solar Panels -->
      <line x1="290" y1="680" x2="190" y2="690" stroke="#94a3b8" stroke-width="2"/>
      <g transform="translate(130, 645) rotate(-8)">
        <rect x="0" y="0" width="85" height="50" rx="2" fill="url(#solarGrad)" stroke="#38bdf8" stroke-width="1.2"/>
        <rect x="0" y="0" width="85" height="50" fill="url(#solarGrid)" opacity="0.6"/>
        <line x1="42.5" y1="0" x2="42.5" y2="50" stroke="#38bdf8" stroke-width="1"/>
        <line x1="0" y1="25" x2="85" y2="25" stroke="#38bdf8" stroke-width="1"/>
      </g>
      <line x1="430" y1="680" x2="520" y2="695" stroke="#94a3b8" stroke-width="2"/>
      <g transform="translate(505, 660) rotate(8)">
        <rect x="0" y="0" width="85" height="50" rx="2" fill="url(#solarGrad)" stroke="#38bdf8" stroke-width="1.2"/>
        <rect x="0" y="0" width="85" height="50" fill="url(#solarGrid)" opacity="0.6"/>
        <line x1="42.5" y1="0" x2="42.5" y2="50" stroke="#38bdf8" stroke-width="1"/>
        <line x1="0" y1="25" x2="85" y2="25" stroke="#38bdf8" stroke-width="1"/>
      </g>

      <!-- Surface Rig -->
      <g transform="translate(480, 770)">
        <rect x="0" y="0" width="18" height="35" fill="#334155" stroke="#94a3b8" stroke-width="1"/>
        <line x1="9" y1="0" x2="9" y2="45" stroke="#f59e0b" stroke-width="1.5"/>
        <ellipse cx="9" cy="45" rx="6" ry="2" fill="#78350f"/>
        <path d="M 0 25 Q -40 35 -75 25" fill="none" stroke="#f59e0b" stroke-width="1.2" stroke-dasharray="3 2"/>
      </g>

      <rect x="230" y="785" width="22" height="15" fill="#64748b" stroke="#cbd5e1" stroke-width="0.8"/>
      <rect x="255" y="788" width="18" height="12" fill="#475569" stroke="#94a3b8" stroke-width="0.8"/>

      <!-- Technical Callouts & Leader Lines (Repositioned for extreme clarity) -->
      <path d="M 360 630 L 360 520 L 270 520" fill="none" stroke="#cbd5e1" stroke-width="1"/>
      <circle cx="360" cy="630" r="2.5" fill="#38bdf8"/>
      <text x="260" y="516" fill="#f8fafc" font-size="11" font-weight="600" text-anchor="end">PRIMARY CARGO LANDER</text>
      <text x="260" y="529" fill="#94a3b8" font-size="10" font-family="monospace" text-anchor="end">Descent Stage / Initial Hab</text>

      <path d="M 150 645 L 150 560 L 190 560" fill="none" stroke="#cbd5e1" stroke-width="1"/>
      <circle cx="150" cy="645" r="2.5" fill="#38bdf8"/>
      <text x="198" y="556" fill="#f8fafc" font-size="11" font-weight="600" text-anchor="start">PHOTOVOLTAIC ARRAY</text>
      <text x="198" y="569" fill="#94a3b8" font-size="10" font-family="monospace" text-anchor="start">25 kWe Deployable Wings</text>

      <path d="M 495 770 L 530 730 L 610 730" fill="none" stroke="#cbd5e1" stroke-width="1"/>
      <circle cx="495" cy="770" r="2.5" fill="#38bdf8"/>
      <text x="615" y="726" fill="#f8fafc" font-size="11" font-weight="600">CORE DRILL &amp; ICE ELEVATOR</text>
      <text x="615" y="739" fill="#94a3b8" font-size="10" font-family="monospace">2.5 L/sol Basal Seepage Test</text>

      <!-- Telemetry Card (Bottom of Era 1) -->
      <g transform="translate(100, 960)">
        <rect x="0" y="0" width="530" height="95" rx="3" fill="#0f172a" stroke="#1e293b" stroke-width="1" fill-opacity="0.9"/>
        <text x="15" y="20" fill="#38bdf8" font-size="10" font-family="monospace" letter-spacing="1">ERA I TELEMETRY SNAPSHOT</text>
        
        <text x="15" y="42" fill="#94a3b8" font-size="11">Excavation Rate:</text>
        <text x="160" y="42" fill="#f8fafc" font-size="12" font-family="monospace" font-weight="600">~280 kg/sol (Rovers)</text>

        <text x="15" y="60" fill="#94a3b8" font-size="11">Hydric Reserve:</text>
        <text x="160" y="60" fill="#38bdf8" font-size="12" font-family="monospace" font-weight="600">3,000 L (Imported floor)</text>

        <text x="15" y="78" fill="#94a3b8" font-size="11">Structural State:</text>
        <text x="160" y="78" fill="#cbd5e1" font-size="12" font-family="monospace" font-weight="600">Single Hull / Surface Anchored</text>

        <line x1="330" y1="15" x2="330" y2="80" stroke="#1e293b" stroke-width="1"/>
        <text x="345" y="42" fill="#94a3b8" font-size="11">O2 Source:</text>
        <text x="430" y="42" fill="#10b981" font-size="12" font-family="monospace" font-weight="600">MOXIE/ISRU</text>

        <text x="345" y="60" fill="#94a3b8" font-size="11">Power Pool:</text>
        <text x="430" y="60" fill="#f59e0b" font-size="12" font-family="monospace" font-weight="600">25 kWe PV</text>
      </g>
    </g>''')

    # =========================================================================
    # ERA II: TRUNK
    # =========================================================================
    svg.append('''<g id="era2_trunk">
      <!-- Era Label Header -->
      <g transform="translate(710, 130)">
        <rect x="0" y="0" width="530" height="60" rx="4" fill="#111827" stroke="#374151" stroke-width="1" fill-opacity="0.8"/>
        <path d="M 0 0 L 0 60" stroke="#f59e0b" stroke-width="4"/>
        <text x="18" y="25" fill="#f59e0b" font-size="11" font-family="monospace" letter-spacing="2">ERA II : TRUNK</text>
        <text x="18" y="47" fill="#f8fafc" font-size="18" font-weight="700">PRIMEIRA PELE &amp; VERTICAL CORE</text>
        <text x="350" y="36" fill="#94a3b8" font-size="12" font-family="monospace">SYNODS 4 – 8</text>
        <text x="350" y="50" fill="#64748b" font-size="11" font-family="monospace">SOLS 2,340 – 7,020</text>
      </g>

      <!-- Berm -->
      <path d="M 830 810 Q 975 750 1120 810 Z" fill="#54210e" stroke="#7a3417" stroke-width="1.5"/>
      <ellipse cx="975" cy="805" rx="145" ry="18" fill="#381509"/>

      <!-- Central Vertical Trunk Tower -->
      <rect x="945" y="450" width="60" height="340" rx="4" fill="url(#trunkGrad)" stroke="#94a3b8" stroke-width="1.8"/>
      <line x1="945" y1="500" x2="1005" y2="500" stroke="#1e293b" stroke-width="2"/>
      <line x1="945" y1="560" x2="1005" y2="560" stroke="#1e293b" stroke-width="2"/>
      <line x1="945" y1="620" x2="1005" y2="620" stroke="#1e293b" stroke-width="2"/>
      <line x1="945" y1="680" x2="1005" y2="680" stroke="#1e293b" stroke-width="2"/>
      <line x1="945" y1="740" x2="1005" y2="740" stroke="#1e293b" stroke-width="2"/>

      <line x1="975" y1="450" x2="975" y2="790" stroke="#38bdf8" stroke-width="1.5" stroke-opacity="0.7"/>

      <path d="M 950 450 Q 975 420 1000 450 Z" fill="#475569" stroke="#cbd5e1" stroke-width="1.5"/>
      <circle cx="975" cy="438" r="6" fill="#0284c7" stroke="#38bdf8" stroke-width="1"/>
      <line x1="975" y1="420" x2="975" y2="385" stroke="#cbd5e1" stroke-width="1.5"/>
      <circle cx="975" cy="385" r="2.5" fill="#f59e0b"/>

      <!-- Radial Arms (First 4) -->
      <path d="M 945 640 L 780 670 L 780 730 L 945 710 Z" fill="#334155" stroke="#64748b" stroke-width="1.5"/>
      <line x1="820" y1="662" x2="820" y2="722" stroke="#94a3b8" stroke-width="1"/>
      <line x1="860" y1="655" x2="860" y2="717" stroke="#94a3b8" stroke-width="1"/>
      <line x1="900" y1="648" x2="900" y2="712" stroke="#94a3b8" stroke-width="1"/>
      <polygon points="775,730 785,730 790,795 770,795" fill="#475569" stroke="#94a3b8" stroke-width="1"/>
      <ellipse cx="780" cy="795" rx="20" ry="6" fill="#1e293b" stroke="#64748b" stroke-width="1"/>

      <path d="M 1005 640 L 1170 670 L 1170 730 L 1005 710 Z" fill="#334155" stroke="#64748b" stroke-width="1.5"/>
      <line x1="1050" y1="648" x2="1050" y2="712" stroke="#94a3b8" stroke-width="1"/>
      <line x1="1090" y1="655" x2="1090" y2="717" stroke="#94a3b8" stroke-width="1"/>
      <line x1="1130" y1="662" x2="1130" y2="722" stroke="#94a3b8" stroke-width="1"/>
      <polygon points="1165,730 1175,730 1180,795 1160,795" fill="#475569" stroke="#94a3b8" stroke-width="1"/>
      <ellipse cx="1170" cy="795" rx="20" ry="6" fill="#1e293b" stroke="#64748b" stroke-width="1"/>

      <polygon points="985,690 1060,730 1055,765 985,735" fill="#1e293b" stroke="#475569" stroke-width="1.2"/>
      <polygon points="965,690 890,730 895,765 965,735" fill="#1e293b" stroke="#475569" stroke-width="1.2"/>

      <g transform="translate(1185, 765)">
        <polygon points="10,0 35,0 40,25 5,25" fill="#78350f" stroke="#f59e0b" stroke-width="1"/>
        <ellipse cx="22" cy="0" rx="12" ry="4" fill="#f59e0b" opacity="0.8"/>
        <rect x="45" y="10" width="20" height="15" fill="#64748b" stroke="#94a3b8" stroke-width="0.8"/>
        <line x1="45" y1="15" x2="65" y2="15" stroke="#475569"/>
        <line x1="45" y1="20" x2="65" y2="20" stroke="#475569"/>
      </g>

      <!-- Technical Callouts & Leader Lines -->
      <path d="M 975 480 L 975 350 L 870 350" fill="none" stroke="#cbd5e1" stroke-width="1"/>
      <circle cx="975" cy="480" r="2.5" fill="#f59e0b"/>
      <text x="860" y="346" fill="#f8fafc" font-size="11" font-weight="600" text-anchor="end">CENTRAL TRUNK CORE</text>
      <text x="860" y="359" fill="#94a3b8" font-size="10" font-family="monospace" text-anchor="end">Basalt Geopolymer Silo</text>

      <path d="M 830 670 L 760 620 L 710 620" fill="none" stroke="#cbd5e1" stroke-width="1"/>
      <circle cx="830" cy="670" r="2.5" fill="#f59e0b"/>
      <text x="700" y="616" fill="#f8fafc" font-size="11" font-weight="600" text-anchor="end">FIRST RADIAL ARMS (#1–#4)</text>
      <text x="700" y="629" fill="#94a3b8" font-size="10" font-family="monospace" text-anchor="end">Anchored Cantilever Spines</text>

      <path d="M 975 805 L 1040 850 L 1140 850" fill="none" stroke="#ef4444" stroke-width="1.2"/>
      <circle cx="975" cy="805" r="3" fill="#ef4444"/>
      <text x="1148" y="846" fill="#ef4444" font-size="11" font-weight="700">HISTORICAL WATER MINIMUM</text>
      <text x="1148" y="859" fill="#cbd5e1" font-size="10" font-family="monospace">2,003 L Floor (Sol ~3,500)</text>

      <!-- Telemetry Card (Bottom of Era 2) -->
      <g transform="translate(710, 960)">
        <rect x="0" y="0" width="530" height="95" rx="3" fill="#0f172a" stroke="#1e293b" stroke-width="1" fill-opacity="0.9"/>
        <text x="15" y="20" fill="#f59e0b" font-size="10" font-family="monospace" letter-spacing="1">ERA II TELEMETRY SNAPSHOT</text>
        
        <text x="15" y="42" fill="#94a3b8" font-size="11">Excavation Rate:</text>
        <text x="160" y="42" fill="#f8fafc" font-size="12" font-family="monospace" font-weight="600">85–280 kg/sol (Recycling)</text>

        <text x="15" y="60" fill="#94a3b8" font-size="11">Hydric Reserve:</text>
        <text x="160" y="60" fill="#ef4444" font-size="12" font-family="monospace" font-weight="600">2,003 L min (Ice elevator ramp)</text>

        <text x="15" y="78" fill="#94a3b8" font-size="11">Structural State:</text>
        <text x="160" y="78" fill="#cbd5e1" font-size="12" font-family="monospace" font-weight="600">4 Radial Arms / Berm Cast</text>

        <line x1="330" y1="15" x2="330" y2="80" stroke="#1e293b" stroke-width="1"/>
        <text x="345" y="42" fill="#94a3b8" font-size="11">Fe Output:</text>
        <text x="430" y="42" fill="#cbd5e1" font-size="12" font-family="monospace" font-weight="600">Pilot Smelting</text>

        <text x="345" y="60" fill="#94a3b8" font-size="11">Power Pool:</text>
        <text x="430" y="60" fill="#f59e0b" font-size="12" font-family="monospace" font-weight="600">100 kWe Fission</text>
      </g>
    </g>''')

    # =========================================================================
    # ERA III: CANOPY
    # =========================================================================
    svg.append('''<g id="era3_canopy">
      <!-- Era Label Header -->
      <g transform="translate(1320, 130)">
        <rect x="0" y="0" width="530" height="60" rx="4" fill="#111827" stroke="#374151" stroke-width="1" fill-opacity="0.8"/>
        <path d="M 0 0 L 0 60" stroke="#38bdf8" stroke-width="4"/>
        <text x="18" y="25" fill="#38bdf8" font-size="11" font-family="monospace" letter-spacing="2">ERA III : CANOPY</text>
        <text x="18" y="47" fill="#f8fafc" font-size="18" font-weight="700">12-ARM MESH &amp; SOIL-WASH PLANT</text>
        <text x="350" y="36" fill="#94a3b8" font-size="12" font-family="monospace">SYNODS 9 – 16</text>
        <text x="350" y="50" fill="#64748b" font-size="11" font-family="monospace">SOLS 7,020 – 13,260</text>
      </g>

      <!-- Excavator Fleet Ring Trackway -->
      <ellipse cx="1585" cy="800" rx="240" ry="45" fill="none" stroke="#64748b" stroke-width="1.8" stroke-dasharray="8 6"/>
      <ellipse cx="1585" cy="800" rx="260" ry="50" fill="none" stroke="#475569" stroke-width="1" stroke-opacity="0.5"/>

      <!-- SoilWashPlant Industrial Complex -->
      <g transform="translate(1380, 680)">
        <rect x="0" y="10" width="16" height="75" rx="3" fill="#475569" stroke="#94a3b8" stroke-width="1"/>
        <rect x="22" y="0" width="18" height="85" rx="3" fill="#64748b" stroke="#cbd5e1" stroke-width="1.2"/>
        <rect x="46" y="15" width="16" height="70" rx="3" fill="#475569" stroke="#94a3b8" stroke-width="1"/>
        <path d="M 8 30 L 31 20 L 54 35" fill="none" stroke="#38bdf8" stroke-width="1.5"/>
        <path d="M 8 60 L 31 50 L 54 65" fill="none" stroke="#38bdf8" stroke-width="1.5"/>
        <circle cx="75" cy="65" r="16" fill="#334155" stroke="#f59e0b" stroke-width="1.2"/>
        <circle cx="75" cy="65" r="10" fill="#0f172a"/>
        <polygon points="95,50 115,50 120,85 90,85" fill="#475569" stroke="#cbd5e1" stroke-width="1"/>
      </g>

      <!-- 12-Arm Radial Station Structure -->
      <circle cx="1585" cy="690" r="32" fill="#1e293b" stroke="#cbd5e1" stroke-width="2"/>
      <circle cx="1585" cy="690" r="18" fill="#334155" stroke="#38bdf8" stroke-width="1.5"/>
      <circle cx="1585" cy="690" r="6" fill="#38bdf8"/>

      <ellipse cx="1585" cy="690" rx="90" ry="32" fill="none" stroke="#64748b" stroke-width="1.5"/>
      <ellipse cx="1585" cy="690" rx="160" ry="55" fill="none" stroke="#94a3b8" stroke-width="1.8"/>

      <!-- 12 Radial Arms -->
      <line x1="1617" y1="690" x2="1745" y2="690" stroke="#cbd5e1" stroke-width="3"/>
      <circle cx="1745" cy="690" r="5" fill="#475569" stroke="#38bdf8" stroke-width="1"/>

      <line x1="1553" y1="690" x2="1425" y2="690" stroke="#cbd5e1" stroke-width="3"/>
      <circle cx="1425" cy="690" r="5" fill="#475569" stroke="#38bdf8" stroke-width="1"/>

      <line x1="1585" y1="658" x2="1585" y2="635" stroke="#cbd5e1" stroke-width="3"/>
      <circle cx="1585" cy="635" r="5" fill="#475569" stroke="#38bdf8" stroke-width="1"/>

      <line x1="1585" y1="722" x2="1585" y2="745" stroke="#cbd5e1" stroke-width="3"/>
      <circle cx="1585" cy="745" r="5" fill="#475569" stroke="#38bdf8" stroke-width="1"/>

      <line x1="1612" y1="675" x2="1725" y2="648" stroke="#94a3b8" stroke-width="2.5"/>
      <line x1="1558" y1="675" x2="1445" y2="648" stroke="#94a3b8" stroke-width="2.5"/>

      <line x1="1612" y1="705" x2="1725" y2="732" stroke="#94a3b8" stroke-width="2.5"/>
      <line x1="1558" y1="705" x2="1445" y2="732" stroke="#94a3b8" stroke-width="2.5"/>

      <line x1="1600" y1="662" x2="1670" y2="638" stroke="#64748b" stroke-width="2"/>
      <line x1="1570" y1="662" x2="1500" y2="638" stroke="#64748b" stroke-width="2"/>

      <line x1="1600" y1="718" x2="1670" y2="742" stroke="#64748b" stroke-width="2"/>
      <line x1="1570" y1="718" x2="1500" y2="742" stroke="#64748b" stroke-width="2"/>

      <!-- Foundation pylons -->
      <g stroke="#475569" stroke-width="1.2">
        <line x1="1745" y1="695" x2="1745" y2="795"/>
        <line x1="1425" y1="695" x2="1425" y2="795"/>
        <line x1="1725" y1="735" x2="1725" y2="815"/>
        <line x1="1445" y1="735" x2="1445" y2="815"/>
      </g>

      <!-- Autonomous Excavator Fleet -->
      <g transform="translate(1710, 810)">
        <rect x="0" y="0" width="32" height="14" rx="2" fill="#f59e0b" stroke="#78350f" stroke-width="1"/>
        <ellipse cx="6" cy="14" rx="5" ry="4" fill="#0f172a" stroke="#64748b" stroke-width="0.8"/>
        <ellipse cx="16" cy="14" rx="5" ry="4" fill="#0f172a" stroke="#64748b" stroke-width="0.8"/>
        <ellipse cx="26" cy="14" rx="5" ry="4" fill="#0f172a" stroke="#64748b" stroke-width="0.8"/>
        <path d="M 32 6 L 44 2 L 42 12 Z" fill="#64748b" stroke="#334155"/>
      </g>

      <g transform="translate(1410, 815)">
        <rect x="0" y="0" width="28" height="12" rx="2" fill="#f59e0b" stroke="#78350f" stroke-width="1"/>
        <ellipse cx="5" cy="12" rx="4" ry="3" fill="#0f172a"/>
        <ellipse cx="14" cy="12" rx="4" ry="3" fill="#0f172a"/>
        <ellipse cx="23" cy="12" rx="4" ry="3" fill="#0f172a"/>
      </g>

      <!-- Sintered Brick & Steel Yard -->
      <g transform="translate(1760, 720)">
        <rect x="0" y="0" width="35" height="25" fill="url(#brickPattern)" stroke="#451a03" stroke-width="1"/>
        <line x1="10" y1="-15" x2="10" y2="0" stroke="#cbd5e1" stroke-width="1.5"/>
        <line x1="0" y1="-15" x2="25" y2="-15" stroke="#f59e0b" stroke-width="1.5"/>
      </g>

      <!-- Technical Callouts & Leader Lines (Repositioned for extreme cleanliness) -->
      <path d="M 1660 638 L 1660 490 L 1560 490" fill="none" stroke="#cbd5e1" stroke-width="1"/>
      <circle cx="1660" cy="638" r="2.5" fill="#38bdf8"/>
      <text x="1550" y="486" fill="#f8fafc" font-size="11" font-weight="600" text-anchor="end">12-ARM RADIAL CANOPY</text>
      <text x="1550" y="499" fill="#94a3b8" font-size="10" font-family="monospace" text-anchor="end">Self-Manufactured Fe Lattice</text>

      <path d="M 1402 680 L 1402 560 L 1330 560" fill="none" stroke="#cbd5e1" stroke-width="1"/>
      <circle cx="1402" cy="680" r="2.5" fill="#38bdf8"/>
      <text x="1320" y="556" fill="#f8fafc" font-size="11" font-weight="600" text-anchor="end">SOILWASH PLANT (v19)</text>
      <text x="1320" y="569" fill="#94a3b8" font-size="10" font-family="monospace" text-anchor="end">800 kg/sol | ClO4 Extraction</text>

      <path d="M 1725 825 L 1725 870 L 1660 870" fill="none" stroke="#cbd5e1" stroke-width="1"/>
      <circle cx="1725" cy="825" r="2.5" fill="#f59e0b"/>
      <text x="1650" y="866" fill="#f8fafc" font-size="11" font-weight="600" text-anchor="end">EXCAVATOR FLEET RING</text>
      <text x="1650" y="879" fill="#94a3b8" font-size="10" font-family="monospace" text-anchor="end">840 kg/sol | Auto-cannibalization</text>

      <!-- Telemetry Card (Bottom of Era 3) -->
      <g transform="translate(1320, 960)">
        <rect x="0" y="0" width="530" height="95" rx="3" fill="#0f172a" stroke="#1e293b" stroke-width="1" fill-opacity="0.9"/>
        <text x="15" y="20" fill="#38bdf8" font-size="10" font-family="monospace" letter-spacing="1">ERA III TELEMETRY SNAPSHOT</text>
        
        <text x="15" y="42" fill="#94a3b8" font-size="11">Excavation Rate:</text>
        <text x="160" y="42" fill="#f8fafc" font-size="12" font-family="monospace" font-weight="600">840 kg/sol (Industrial fleet)</text>

        <text x="15" y="60" fill="#94a3b8" font-size="11">Perchlorate Detox:</text>
        <text x="160" y="60" fill="#38bdf8" font-size="12" font-family="monospace" font-weight="600">~79 t ClO4 -&gt; Refined O2</text>

        <text x="15" y="78" fill="#94a3b8" font-size="11">Structural Fe:</text>
        <text x="160" y="78" fill="#cbd5e1" font-size="12" font-family="monospace" font-weight="600">1,732 t locally manufactured</text>

        <line x1="330" y1="15" x2="330" y2="80" stroke="#1e293b" stroke-width="1"/>
        <text x="345" y="42" fill="#94a3b8" font-size="11">Geopolymer:</text>
        <text x="430" y="42" fill="#cbd5e1" font-size="12" font-family="monospace" font-weight="600">2,616 t cmt</text>

        <text x="345" y="60" fill="#94a3b8" font-size="11">Fleet Health:</text>
        <text x="430" y="60" fill="#f59e0b" font-size="12" font-family="monospace" font-weight="600">659 reconds</text>
      </g>
    </g>''')

    # =========================================================================
    # ERA IV: ECOPOIESIS
    # =========================================================================
    svg.append('''<g id="era4_ecopoiesis">
      <!-- Era Label Header -->
      <g transform="translate(1930, 130)">
        <rect x="0" y="0" width="530" height="60" rx="4" fill="#111827" stroke="#374151" stroke-width="1" fill-opacity="0.8"/>
        <path d="M 0 0 L 0 60" stroke="#10b981" stroke-width="4"/>
        <text x="18" y="25" fill="#10b981" font-size="11" font-family="monospace" letter-spacing="2">ERA IV : ECOPOIESIS</text>
        <text x="18" y="47" fill="#f8fafc" font-size="18" font-weight="700">BIOSPHERE &amp; CLEANED SOIL HALO</text>
        <text x="350" y="36" fill="#94a3b8" font-size="12" font-family="monospace">SYNODS 17 – 27</text>
        <text x="350" y="50" fill="#64748b" font-size="11" font-family="monospace">SOLS 13,260 – 21,060</text>
      </g>

      <!-- Cleaned Soil Halo with Expanding Concentric Contour Waves -->
      <ellipse cx="2195" cy="800" rx="285" ry="62" fill="url(#haloGrad)"/>
      <ellipse cx="2195" cy="800" rx="225" ry="48" fill="#1c472d" opacity="0.6"/>
      <ellipse cx="2195" cy="800" rx="160" ry="34" fill="#245939" opacity="0.5"/>
      
      <!-- Halo Boundary Contour Rings -->
      <ellipse cx="2195" cy="800" rx="285" ry="62" fill="none" stroke="#34d399" stroke-width="1.8" stroke-dasharray="6 4" filter="url(#glowGreen)" opacity="0.7"/>
      <ellipse cx="2195" cy="800" rx="240" ry="52" fill="none" stroke="#10b981" stroke-width="1" stroke-opacity="0.5"/>
      <ellipse cx="2195" cy="800" rx="190" ry="40" fill="none" stroke="#059669" stroke-width="0.8" stroke-opacity="0.4"/>

      <!-- Radial Structural Arms Baseline -->
      <g stroke="#475569" stroke-width="2">
        <line x1="2195" y1="675" x2="2040" y2="710"/>
        <line x1="2195" y1="675" x2="2350" y2="710"/>
        <line x1="2195" y1="675" x2="2195" y2="760"/>
        <line x1="2195" y1="675" x2="2120" y2="630"/>
        <line x1="2195" y1="675" x2="2270" y2="630"/>
      </g>

      <!-- Center Biome Core Tower -->
      <rect x="2180" y="470" width="30" height="200" rx="3" fill="#1e293b" stroke="#64748b" stroke-width="1.5"/>
      <line x1="2195" y1="470" x2="2195" y2="410" stroke="#cbd5e1" stroke-width="1.5"/>
      <circle cx="2195" cy="410" r="3" fill="#10b981"/>

      <!-- Geodesic Greenhouse Biodomes Glowing Emerald Green -->
      <g filter="url(#glowGreen)">
        <path d="M 2135 675 Q 2195 565 2255 675 Z" fill="url(#domeGlow)" stroke="#34d399" stroke-width="2"/>
        <path d="M 2160 675 L 2195 600 L 2230 675" fill="none" stroke="#a7f3d0" stroke-width="1" stroke-opacity="0.8"/>
        <line x1="2145" y1="640" x2="2245" y2="640" stroke="#a7f3d0" stroke-width="0.8" stroke-opacity="0.7"/>
        <line x1="2195" y1="600" x2="2195" y2="675" stroke="#a7f3d0" stroke-width="0.8" stroke-opacity="0.8"/>
      </g>

      <g filter="url(#glowGreen)">
        <path d="M 2030 710 Q 2080 615 2130 710 Z" fill="url(#domeGlow)" stroke="#34d399" stroke-width="1.8"/>
        <path d="M 2050 710 L 2080 645 L 2110 710" fill="none" stroke="#a7f3d0" stroke-width="0.8" stroke-opacity="0.7"/>
        <line x1="2080" y1="645" x2="2080" y2="710" stroke="#a7f3d0" stroke-width="0.8" stroke-opacity="0.7"/>
      </g>

      <g filter="url(#glowGreen)">
        <path d="M 2260 710 Q 2310 615 2360 710 Z" fill="url(#domeGlow)" stroke="#34d399" stroke-width="1.8"/>
        <path d="M 2280 710 L 2310 645 L 2340 710" fill="none" stroke="#a7f3d0" stroke-width="0.8" stroke-opacity="0.7"/>
        <line x1="2310" y1="645" x2="2310" y2="710" stroke="#a7f3d0" stroke-width="0.8" stroke-opacity="0.7"/>
      </g>

      <g filter="url(#glowGreen)">
        <path d="M 2155 745 Q 2195 680 2235 745 Z" fill="url(#domeGlow)" stroke="#6ee7b7" stroke-width="1.5"/>
      </g>

      <!-- External Heavy Haulers in Cleaned Soil Field -->
      <g transform="translate(2350, 805)">
        <rect x="0" y="0" width="38" height="16" rx="2" fill="#475569" stroke="#94a3b8" stroke-width="1"/>
        <ellipse cx="8" cy="16" rx="6" ry="4" fill="#0f172a" stroke="#34d399" stroke-width="1"/>
        <ellipse cx="19" cy="16" rx="6" ry="4" fill="#0f172a" stroke="#34d399" stroke-width="1"/>
        <ellipse cx="30" cy="16" rx="6" ry="4" fill="#0f172a" stroke="#34d399" stroke-width="1"/>
        <polygon points="6,0 32,0 28,-6 10,-6" fill="#1b3824"/>
      </g>

      <g transform="translate(2010, 815)">
        <rect x="0" y="0" width="30" height="13" rx="2" fill="#475569" stroke="#94a3b8" stroke-width="1"/>
        <ellipse cx="6" cy="13" rx="5" ry="3.5" fill="#0f172a"/>
        <ellipse cx="15" cy="13" rx="5" ry="3.5" fill="#0f172a"/>
        <ellipse cx="24" cy="13" rx="5" ry="3.5" fill="#0f172a"/>
      </g>

      <!-- Technical Callouts & Leader Lines -->
      <path d="M 2195 565 L 2195 380 L 2290 380" fill="none" stroke="#cbd5e1" stroke-width="1"/>
      <circle cx="2195" cy="565" r="2.5" fill="#10b981"/>
      <text x="2298" y="376" fill="#f8fafc" font-size="11" font-weight="600">GEODESIC GREENHOUSE BIOMES</text>
      <text x="2298" y="389" fill="#10b981" font-size="10" font-family="monospace">Spirulina + Crops | 56% O2 Generation</text>

      <path d="M 2390 770 L 2430 730 L 2510 730" fill="none" stroke="#34d399" stroke-width="1.2"/>
      <circle cx="2390" cy="770" r="2.5" fill="#34d399"/>
      <text x="2500" y="726" fill="#f8fafc" font-size="11" font-weight="600" text-anchor="end">DETOXIFIED CLEAN SOIL HALO</text>
      <text x="2500" y="739" fill="#34d399" font-size="10" font-family="monospace" text-anchor="end">52,294 t Substrate Remediated</text>

      <path d="M 2195 760 L 2240 850 L 2320 850" fill="none" stroke="#38bdf8" stroke-width="1"/>
      <circle cx="2195" cy="760" r="2.5" fill="#38bdf8"/>
      <text x="2328" y="846" fill="#f8fafc" font-size="11" font-weight="600">NET HYDRIC RESERVE</text>
      <text x="2328" y="859" fill="#38bdf8" font-size="10" font-family="monospace">+519.5 kL Surplus at Sol 21,060</text>

      <!-- Telemetry Card (Bottom of Era 4) -->
      <g transform="translate(1930, 960)">
        <rect x="0" y="0" width="530" height="95" rx="3" fill="#0f172a" stroke="#1e293b" stroke-width="1" fill-opacity="0.9"/>
        <text x="15" y="20" fill="#10b981" font-size="10" font-family="monospace" letter-spacing="1">ERA IV TELEMETRY SNAPSHOT</text>
        
        <text x="15" y="42" fill="#94a3b8" font-size="11">Excavation Rate:</text>
        <text x="160" y="42" fill="#f8fafc" font-size="12" font-family="monospace" font-weight="600">~1,700 kg/sol (Heavy Haulers)</text>

        <text x="15" y="60" fill="#94a3b8" font-size="11">Total Clean Soil:</text>
        <text x="160" y="60" fill="#10b981" font-size="12" font-family="monospace" font-weight="600">52,294 t (Detox halo closed)</text>

        <text x="15" y="78" fill="#94a3b8" font-size="11">Oxygen Output:</text>
        <text x="160" y="78" fill="#38bdf8" font-size="12" font-family="monospace" font-weight="600">2,293.9 t (56% photo / 36% elec)</text>

        <line x1="330" y1="15" x2="330" y2="80" stroke="#1e293b" stroke-width="1"/>
        <text x="345" y="42" fill="#94a3b8" font-size="11">Hydric End:</text>
        <text x="430" y="42" fill="#38bdf8" font-size="12" font-family="monospace" font-weight="600">+519.5 kL</text>

        <text x="345" y="60" fill="#94a3b8" font-size="11">Integrity:</text>
        <text x="430" y="60" fill="#10b981" font-size="12" font-family="monospace" font-weight="600">0.569 (Stable)</text>
      </g>
    </g>''')

    # =========================================================================
    # TIMELINE SPINE & EVENT RAIL (LOWER SECTION)
    # =========================================================================
    spine_x0 = 100
    spine_w = 2360
    synod_step = spine_w / 27.0
    spine_y = 1205

    svg.append(f'''<g id="timelineSpine">
      <text x="100" y="1095" fill="#38bdf8" font-size="12" font-family="monospace" letter-spacing="2">TEMPORAL SPINE // SYNODIC PROGRESSION &amp; METABOLIC EVENTS</text>
      <text x="2460" y="1095" fill="#94a3b8" font-size="11" font-family="monospace" text-anchor="end">TOTAL DURATION: 27 SYNODS = 21,060 SOLS (1 SYNOD = 780 SOLS)</text>

      <rect x="100" y="1108" width="2360" height="248" fill="#0a0d14" stroke="#1e293b" stroke-width="1" rx="4"/>

      <!-- Main Horizontal Spine Bar -->
      <line x1="{spine_x0}" y1="{spine_y}" x2="{spine_x0 + spine_w}" y2="{spine_y}" stroke="url(#spineGrad)" stroke-width="4" stroke-linecap="round"/>
      <line x1="{spine_x0}" y1="{spine_y + 4}" x2="{spine_x0 + spine_w}" y2="{spine_y + 4}" stroke="#0f172a" stroke-width="1"/>

      <!-- Era Shading Blocks below timeline -->
      <!-- Era 1: S0 to S3 -->
      <rect x="{spine_x0}" y="{spine_y + 12}" width="{3 * synod_step}" height="26" fill="#38bdf8" fill-opacity="0.12" stroke="#38bdf8" stroke-width="0.8"/>
      <text x="{spine_x0 + 1.5 * synod_step}" y="{spine_y + 29}" fill="#38bdf8" font-size="11" font-family="monospace" font-weight="700" text-anchor="middle">ERA I : ANCHORAGE (0 – 2,340 SOLS)</text>

      <!-- Era 2: S3 to S8 -->
      <rect x="{spine_x0 + 3 * synod_step}" y="{spine_y + 12}" width="{5 * synod_step}" height="26" fill="#f59e0b" fill-opacity="0.12" stroke="#f59e0b" stroke-width="0.8"/>
      <text x="{spine_x0 + 5.5 * synod_step}" y="{spine_y + 29}" fill="#f59e0b" font-size="11" font-family="monospace" font-weight="700" text-anchor="middle">ERA II : TRUNK (2,340 – 7,020 SOLS)</text>

      <!-- Era 3: S8 to S16 -->
      <rect x="{spine_x0 + 8 * synod_step}" y="{spine_y + 12}" width="{8 * synod_step}" height="26" fill="#38bdf8" fill-opacity="0.12" stroke="#38bdf8" stroke-width="0.8"/>
      <text x="{spine_x0 + 12 * synod_step}" y="{spine_y + 29}" fill="#38bdf8" font-size="11" font-family="monospace" font-weight="700" text-anchor="middle">ERA III : CANOPY (7,020 – 13,260 SOLS)</text>

      <!-- Era 4: S16 to S27 -->
      <rect x="{spine_x0 + 16 * synod_step}" y="{spine_y + 12}" width="{11 * synod_step}" height="26" fill="#10b981" fill-opacity="0.12" stroke="#10b981" stroke-width="0.8"/>
      <text x="{spine_x0 + 21.5 * synod_step}" y="{spine_y + 29}" fill="#10b981" font-size="11" font-family="monospace" font-weight="700" text-anchor="middle">ERA IV : ECOPOIESIS (13,260 – 21,060 SOLS)</text>
    ''')

    # Add 28 Synod Ticks (0 to 27) and Sol Annotations
    for s in range(28):
        x = spine_x0 + s * synod_step
        sols = s * 780
        if s in [0, 3, 8, 16, 27]:
            t_len = 16
            color = "#f8fafc"
            sw = 2.0
        elif s % 2 == 0:
            t_len = 10
            color = "#cbd5e1"
            sw = 1.2
        else:
            t_len = 6
            color = "#64748b"
            sw = 0.8
        
        svg.append(f'<line x1="{x:.1f}" y1="{spine_y - t_len}" x2="{x:.1f}" y2="{spine_y + t_len}" stroke="{color}" stroke-width="{sw}"/>')
        
        if s % 2 == 0 or s in [3, 27]:
            svg.append(f'<text x="{x:.1f}" y="{spine_y - 18}" fill="{color}" font-size="10" font-family="monospace" font-weight="600" text-anchor="middle">S{s}</text>')
            svg.append(f'<text x="{x:.1f}" y="{spine_y - 6}" fill="#64748b" font-size="8" font-family="monospace" text-anchor="middle">{sols}</text>')

    # Minor Sol sub-ticks between synods
    for sol_step in range(0, 21060 + 1, 260):
        s_frac = sol_step / 780.0
        x_sub = spine_x0 + s_frac * synod_step
        svg.append(f'<line x1="{x_sub:.1f}" y1="{spine_y - 3}" x2="{x_sub:.1f}" y2="{spine_y + 3}" stroke="#334155" stroke-width="0.5"/>')

    # =========================================================================
    # BREAK-EVEN POINT MARKER (PROMINENT AT S16.5)
    # =========================================================================
    be_synod = 16.5
    be_x = spine_x0 + be_synod * synod_step
    svg.append(f'''<!-- ISRU Break-Even Point Callout -->
    <g id="breakEvenMarker" filter="url(#glowGold)">
      <line x1="{be_x:.1f}" y1="{spine_y}" x2="{be_x:.1f}" y2="1120" stroke="#f59e0b" stroke-width="2"/>
      <polygon points="{be_x:.1f},{spine_y - 14} {be_x + 9:.1f},{spine_y} {be_x:.1f},{spine_y + 14} {be_x - 9:.1f},{spine_y}" fill="#f59e0b" stroke="#ffffff" stroke-width="1.8"/>
      <circle cx="{be_x:.1f}" cy="{spine_y}" r="2.5" fill="#0f172a"/>

      <g transform="translate({be_x - 170:.1f}, 1115)">
        <rect x="0" y="0" width="340" height="40" rx="4" fill="#1e1808" stroke="#f59e0b" stroke-width="1.5" fill-opacity="0.96"/>
        <text x="170" y="16" fill="#f59e0b" font-size="11" font-family="monospace" font-weight="800" text-anchor="middle">◆ ISRU BREAK-EVEN POINT (SYNOD 16–17)</text>
        <text x="170" y="31" fill="#fef08a" font-size="10" font-family="monospace" text-anchor="middle">LOCAL MASS (2,911 t) &gt; EARTH IMPORT (2,400 t) [1.21x]</text>
      </g>
    </g>''')

    # =========================================================================
    # SPROUTING EVENTS (ABOVE THE TIMELINE SPINE - GROWING UPWARD)
    # =========================================================================
    def render_sprouting(synod, sol, label, y_box, align_left=False):
        sx = spine_x0 + synod * synod_step
        anchor = "end" if align_left else "start"
        tx = -12 if align_left else 12
        return f'''<g transform="translate({sx:.1f}, {y_box})">
          <line x1="0" y1="18" x2="0" y2="{spine_y - y_box}" stroke="#10b981" stroke-width="1.2" stroke-dasharray="2 2"/>
          <circle cx="0" cy="{spine_y - y_box}" r="3" fill="#10b981"/>
          <!-- Sprout Badge -->
          <polygon points="0,-10 9,-3 6,8 -6,8 -9,-3" fill="#064e3b" stroke="#34d399" stroke-width="1.2"/>
          <path d="M 0 4 Q -3 -2 0 -6 Q 3 -2 0 4 Z" fill="#34d399"/>
          <!-- Text -->
          <text x="{tx}" y="-1" fill="#34d399" font-size="9" font-family="monospace" font-weight="700" text-anchor="{anchor}">SPROUT: {label}</text>
          <text x="{tx}" y="10" fill="#94a3b8" font-size="8" font-family="monospace" text-anchor="{anchor}">Sol {sol}</text>
        </g>'''

    # =========================================================================
    # ABSCISSION EVENTS (BELOW THE TIMELINE ERA BANDS - SHEDDING DOWNWARD)
    # =========================================================================
    def render_abscission(synod, sol, label, y_box):
        sx = spine_x0 + synod * synod_step
        return f'''<g transform="translate({sx:.1f}, {y_box})">
          <line x1="0" y1="-8" x2="0" y2="{spine_y + 38 - y_box}" stroke="#f97316" stroke-width="1.2" stroke-dasharray="2 2"/>
          <circle cx="0" cy="{spine_y + 38 - y_box}" r="3" fill="#f97316"/>
          <!-- Abscission Badge -->
          <polygon points="0,10 9,3 6,-8 -6,-8 -9,3" fill="#431407" stroke="#f97316" stroke-width="1.2"/>
          <path d="M 0 -3 Q 3 2 0 6 Q -3 2 0 -3 Z" fill="#fb923c"/>
          <!-- Text -->
          <text x="12" y="1" fill="#fb923c" font-size="9" font-family="monospace" font-weight="700">ABSCISSION: {label}</text>
          <text x="12" y="12" fill="#94a3b8" font-size="8" font-family="monospace">Sol {sol} (Cannibalized &amp; Recycled)</text>
        </g>'''

    svg.append('<!-- Sprouting Events (Above Spine) -->')
    svg.append(render_sprouting(4.2, 3276, "Arms #1–#4 (Trunk Phase)", 1138))
    svg.append(render_sprouting(9.5, 7410, "Arms #5–#8 (Canopy Expansion)", 1138))
    svg.append(render_sprouting(13.5, 10530, "Arms #9–#12 (12-Arm Closure)", 1168, align_left=False))
    svg.append(render_sprouting(19.2, 14976, "Biodome Cluster #1 (Ecopoiesis)", 1138))
    svg.append(render_sprouting(24.5, 19110, "Clean Soil Halo Expansion", 1138))

    svg.append('<!-- Abscission Events (Below Spine Era Bands) -->')
    svg.append(render_abscission(5.8, 4524, "Arm #2 Thermal Jettison", 1270))
    svg.append(render_abscission(11.2, 8736, "Arm #5 Storm Fracture", 1270))
    svg.append(render_abscission(15.0, 11700, "Fleet Gen-1 Rover Re-melt", 1270))
    svg.append(render_abscission(21.5, 16770, "Aux Truss Shedding (Biome Clear)", 1270))

    # =========================================================================
    # FOOTER & LEGEND (BOTTOM MARGIN)
    # =========================================================================
    svg.append('''<g id="footerLegend" transform="translate(100, 1378)">
      <rect x="0" y="0" width="2360" height="42" rx="3" fill="#0b0f19" stroke="#1e293b" stroke-width="0.8"/>

      <g transform="translate(25, 25)" font-family="monospace" font-size="11">
        <!-- Sprouting Event Legend -->
        <polygon points="0,-8 6,-3 4,5 -4,5 -6,-3" fill="#064e3b" stroke="#34d399" stroke-width="1.2"/>
        <text x="14" y="0" fill="#34d399" font-weight="700">SPROUTING EVENT</text>
        <text x="145" y="0" fill="#94a3b8">(New structural arm / dome germination from local Fe)</text>

        <!-- Abscission Event Legend -->
        <g transform="translate(620, 0)">
          <polygon points="0,8 6,3 4,-5 -4,-5 -6,3" fill="#431407" stroke="#f97316" stroke-width="1.2"/>
          <text x="14" y="0" fill="#fb923c" font-weight="700">ABSCISSION EVENT</text>
          <text x="155" y="0" fill="#94a3b8">(Controlled module shedding, cannibalization &amp; re-smelting)</text>
        </g>

        <!-- Break-Even Milestone Legend -->
        <g transform="translate(1330, 0)">
          <polygon points="0,-7 6,0 0,7 -6,0" fill="#f59e0b" stroke="#ffffff" stroke-width="1"/>
          <text x="14" y="0" fill="#f59e0b" font-weight="700">BREAK-EVEN MILESTONE</text>
          <text x="175" y="0" fill="#94a3b8">(Manufactured local ISRU mass &gt; Total imported Earth mass)</text>
        </g>

        <text x="2310" y="0" fill="#64748b" text-anchor="end">DOXIHEWU-OMNIMIND MARS-MONOCULTURE v19 // ENGINEERING RECONCILIATION</text>
      </g>
    </g>''')

    svg.append('</g>') # close timelineSpine
    svg.append('</svg>')
    
    return '\n'.join(svg)

if __name__ == '__main__':
    svg_content = build_svg()
    
    # Save SVG alongside PNG in docs/assets
    svg_out = '/home/fahbrain/projects/Doxihewu-OmniMind-MarsStation/docs/assets/mars_synod_timeline.svg'
    with open(svg_out, 'w', encoding='utf-8') as f:
        f.write(svg_content)
    print(f"Saved SVG to: {svg_out} ({len(svg_content)} bytes)")
    
    # Also save to /tmp for convert
    with open('/tmp/mars_synod_timeline.svg', 'w', encoding='utf-8') as f:
        f.write(svg_content)
