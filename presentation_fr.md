# SMO: Supervision et Orchestration Système

**Outil de supervision système en temps réel**

👨‍💻 BILAL SIKI

CYBERSÉCURITÉ S03 - Systèmes et Réseaux III

```
  ____            __  __             
 / ___| _   _ ___|  \/  | ___  _ __  
 \___ \| | | / __| |\/| |/ _ \| '_ \ 
  ___) | |_| \__ \ |  | | (_) | | | |
 |____/ \__, |___/_|  |_|\___/|_| |_|
        |___/                         
```

---

## Introduction

### Aperçu du projet

Le projet **SMO** est un outil de supervision des ressources système en Python, conçu pour suivre et analyser en temps réel les métriques critiques de la machine.

### Objectifs

Développer une solution de supervision complète capable de suivre :

- **CPU :** Utilisation par cœur, fréquence et charges moyennes
- **Mémoire :** RAM physique et analyse du swap
- **Disque :** Opérations de lecture/écriture et utilisation du stockage
- **Réseau :** Statistiques des interfaces et profils de trafic
- **Processus :** Consommation des ressources par processus

### Fonctionnalités clés

- Collecte en temps réel avec intervalles de rafraîchissement configurables
- Interfaces multiples : TUI (terminal), tableau de bord web et CLI
- Journalisation structurée en JSONL pour la persistance des données
- Alertes basées sur des seuils pour une supervision proactive
- Compatibilité multiplateforme (Linux, macOS, Windows)

### Pile technique

- `Python 3.8+` — Langage principal
- `psutil` — Bibliothèque de collecte de métriques système
- `socket` — Module d'identification réseau
- `FastAPI` — Framework backend du tableau de bord web
- `Rich` — Interface utilisateur en terminal (TUI)

---

## Problématique

### La criticité de la supervision système

Dans les environnements serveurs Linux, la **supervision continue** n'est pas optionnelle — elle est essentielle pour garantir la fiabilité des services, optimiser les performances et renforcer la sécurité.

### Défis critiques en production

#### 1. Épuisement des ressources

Sans supervision, les systèmes peuvent connaître une saturation CPU, des fuites mémoire et un manque d'espace disque, entraînant une dégradation du service ou une panne.

- Le « OOM killer » termine des processus critiques
- Un disque plein empêche la journalisation et les écritures
- Le throttling CPU provoque des expirations d'applications

#### 2. Goulots d'étranglement

L'identification des problèmes de performance devient réactive au lieu d'être proactive, ce qui entraîne :

- Un MTTR accru (temps moyen de résolution)
- Des incidents remontés par les utilisateurs plutôt que détectés en interne
- Des difficultés à corréler les symptômes aux causes racines

#### 3. Sécurité et détection d'anomalies

Des profils anormaux de consommation de ressources peuvent indiquer :

- Des mineurs de crypto opérant sur des systèmes compromis
- Du trafic d'attaque DDoS saturant des interfaces réseau
- Des malwares consommant excessivement CPU/mémoire

### Impact métier

| Métrique | Impact |
|----------|--------|
| Coût d'indisponibilité | ≈ 5 600 $/minute (moyenne entreprises) |
| Violations de SLA | Pénalités financières et atteinte à la réputation |
| Planification de capacité | Décisions éclairées de montée en charge |
| Débogage | Analyse accélérée des causes via corrélation des métriques |

---

## Choix de l'outil : Pourquoi Python ?

### Atouts du langage pour la supervision

| Caractéristique | Avantage |
|-----------------|----------|
| **Multi-plateforme** | Un seul code fonctionne sur Linux, macOS, Windows sans modification |
| **Écosystème riche** | psutil, FastAPI, Rich fournissent des composants prêts pour la production |
| **Développement rapide** | Les abstractions de haut niveau réduisent le temps de dev de 40–60 % |
| **Librairie standard** | Les modules socket, json, threading évitent des dépendances externes |
| **Lisibilité du code** | Une syntaxe claire améliore la maintenabilité et la collaboration |

### Comparaison des technologies alternatives

#### Scripts Bash/Shell

❌ Structures de données limitées, gestion d'erreurs faible, difficile à scaler

#### C/C++

✓ Excellentes performances  
❌ Complexité élevée, temps de dev long, gestion mémoire manuelle

#### Go

✓ Concurrence supérieure, typage statique  
❌ Courbe d'apprentissage plus raide, écosystème plus réduit pour la supervision

#### Python

✓ Équilibre optimal entre performance, simplicité et maturité de l'écosystème  
✓ psutil offre des appels système à vitesse C via des interfaces Python

### Considérations de performance

Pour un outil de supervision où la **performance temps réel** (métriques sous la seconde) et la **productivité développeur** sont essentielles, Python est une base idéale. La bibliothèque psutil offre des performances proches du C pour les appels système tout en conservant la simplicité du Python.

```python
# Benchmark de performance : collecte CPU via psutil
# Temps moyen de collecte : ~1,2 ms par appel
# Surcharge : < 0,1 % de l'UC totale du système
```

---

## Bibliothèque clé : psutil

### Interface avec le noyau

La bibliothèque `psutil` (process and system utilities) fournit une **API unifiée** pour accéder aux informations système sur différents OS.

### Mécanismes de communication avec le noyau

#### Linux : Lecture des pseudo-systèmes de fichiers `/proc` et `/sys`

- `/proc/stat` - Statistiques CPU
- `/proc/meminfo` - Informations mémoire
- `/proc/net/dev` - Statistiques d'interfaces réseau
- `/proc/diskstats` - Compteurs d'E/S disque

#### Windows : Utilise les appels aux API Windows

- GetSystemInfo() - Informations système
- GlobalMemoryStatusEx() - État de la mémoire
- GetDiskFreeSpaceEx() - Espace disque

#### macOS : S'appuie sur sysctl et libproc

- sysctl() - Paramètres du noyau
- proc_pidinfo() - Informations sur les processus

### Abstraction des appels système

```python
# Interface directe avec le noyau (conceptuel - Linux)
/proc/stat → CPU counters (user, system, idle, iowait)
/proc/meminfo → Memory metrics (MemTotal, MemFree, Buffers, Cached)
/proc/net/dev → Network interface statistics (bytes, packets, errors)

# Couche d'abstraction psutil (multi-plateforme)
psutil.cpu_percent()       # Agrège les données de /proc/stat
psutil.virtual_memory()    # Analyse /proc/meminfo
psutil.net_io_counters()   # Traite /proc/net/dev
```

### Fonctions clés de psutil

| Fonction | Rôle | Type de retour |
|----------|------|----------------|
| `cpu_percent()` | Pourcentage d'utilisation CPU | float |
| `virtual_memory()` | Statistiques de mémoire physique | namedtuple svmem |
| `disk_usage()` | Utilisation de l'espace disque | namedtuple sdiskusage |
| `net_io_counters()` | Statistiques d'E/S réseau | namedtuple snetio |

### Analyse technique

psutil fait le pont entre le code Python de haut niveau et les opérations bas niveau du noyau, offrant des **performances de niveau production** (extensions compilées en C) sans sacrifier la lisibilité.

---

## Réseau : module socket

### Identification de l'hôte

SMO implémente plusieurs couches d'identification d'hôte pour une attribution précise du système dans des environnements de supervision distribués.

### Hiérarchie d'identification

```
1. Nom d'hôte (socket.gethostname())
    └─> Résolution FQDN via DNS (socket.getfqdn())
   
2. Interfaces réseau (psutil.net_if_addrs())
    ├─> Adresses IPv4 (AF_INET)
    ├─> Adresses IPv6 (AF_INET6)
    └─> Adresses MAC (AF_LINK / AF_PACKET)
   
3. Connexions actives (psutil.net_connections())
    └─> Sockets TCP/UDP avec points de terminaison locaux/distants
```

### Fonctions du module socket

| Fonction | Rôle | Appel système |
|----------|------|---------------|
| `gethostname()` | Récupérer le nom d'hôte | Appel système gethostname() |
| `gethostbyname()` | Effectuer une résolution DNS | Appel système getaddrinfo() |
| `getfqdn()` | Obtenir le nom de domaine complet | Lookup DNS inversé |

### Architecture de remontée distante

#### Interface tableau de bord web

L'API REST basée sur FastAPI expose les métriques via des endpoints HTTP :

- `GET /` — Interface HTML du dashboard
- `GET /api/config` — Récupération de la configuration (JSON)
- `POST /api/config` — Mise à jour dynamique de la configuration
- `POST /api/config/reset` — Réinitialisation aux valeurs par défaut
- `GET /api/logs/export?format=json|csv|markdown` — Export des journaux
- `WebSocket /ws` — Diffusion temps réel des métriques

### Implémentation WebSocket

```python
# Architecture push côté serveur
1. Le client initie la poignée de main WebSocket (Upgrade HTTP)
2. Le serveur lit la dernière métrique depuis le fichier JSONL
3. Les métriques sont sérialisées en JSON et diffusées chaque seconde
4. Le JavaScript côté client met à jour le DOM en temps réel

Avantages :
▸ Faible latence (cycles < 100 ms)
▸ Moins de surcharge HTTP qu'un polling traditionnel
▸ Canal bidirectionnel
▸ Reconnexion automatique en cas de perte
```

### Découverte des interfaces réseau

```python
import psutil
import socket

# Get all network interfaces and their addresses
interfaces = psutil.net_if_addrs()
hostname = socket.gethostname()

for iface_name, addresses in interfaces.items():
    for addr in addresses:
        if addr.family == socket.AF_INET:
            print(f"{hostname} - {iface_name}: {addr.address}")
```

---

## Architecture système

### Décomposition des composants

#### 1. Couche noyau OS

Fournit des métriques brutes via /proc, /sys (Linux), sysctl (macOS) ou les API Windows

#### 2. Couche collecte (metrics/)

Modules spécialisés par type de métrique :

- `cpu.py` — Utilisation par cœur, fréquence, charges, commutations de contexte
- `memory.py` — Mémoire virtuelle, swap, buffers, cache
- `disk.py` — Utilisation des partitions, compteurs d'E/S (octets/ops)
- `network.py` — Statistiques d'interfaces, connexions, analyse de trafic
- `process.py` — Auto-monitoring de l'agent et métriques de processus

#### 3. Couche orchestration (agent.py)

Coordonne la collecte avec des intervalles configurables

- Mises à jour concurrentes via threads
- Gestion de configuration centralisée
- Évaluation des seuils d'alerte

#### 4. Couche persistance (logger.py)

Ajoute des métriques au fichier JSONL pour l'analyse historique

- Logs structurés avec horodatage
- Format lisible et exploitable par machine
- Intégration des alertes en cas de seuil dépassé

#### 5. Couche présentation

**Tableau de bord TUI :** Interface terminal basée sur Rich avec mises à jour en temps réel

**Tableau de bord Web :** Serveur FastAPI avec streaming WebSocket

**CLI :** Interface en ligne de commande pour scripting et automatisation

### Philosophie : séparation des responsabilités

Chaque couche a une **responsabilité unique**, permettant :

- Tests et validations indépendants
- Mises à niveau modulaires sans impact global
- Chemins de débogage et de diagnostic clairs

---

## Implémentation du code

### Collecte du pourcentage CPU

Ci-dessous, l'implémentation montrant comment SMO récupère l'utilisation du CPU :

```python
import psutil
from typing import Dict, Any

class CPUMetrics:
    """Collect CPU performance metrics."""
    
    @staticmethod
    def get_cpu_percent() -> Dict[str, Any]:
        """
        Fetch CPU utilization percentage.
        
        Technical Details:
        - psutil.cpu_percent(interval=1) blocks for 1 second
        - Measures CPU usage by comparing /proc/stat counters
        - Calculates: (total_time - idle_time) / total_time * 100
        - Returns aggregate utilization across all cores
        
        Returns:
            dict: Metric with value, unit, type, and description
        """
        cpu_value = psutil.cpu_percent(interval=1, percpu=False)
        
        return {
            "value": round(cpu_value, 1),
            "unit": "%",
            "type": "dynamic",
            "refresh_interval": 2,
            "description": "Average CPU utilization"
        }
    
    @staticmethod
    def get_per_core_usage() -> Dict[str, Any]:
        """
        Get per-core CPU usage for detailed analysis.
        
        Returns:
            dict: Dictionary mapping core IDs to usage percentages
        """
        per_core = psutil.cpu_percent(interval=1, percpu=True)
        
        result = {}
        for i, usage in enumerate(per_core):
            result[f"core_{i}_usage"] = {
                "value": round(usage, 1),
                "unit": "%",
                "type": "dynamic",
                "refresh_interval": 2,
                "description": f"CPU usage for core {i}"
            }
        return result
    
    @staticmethod
    def get_cpu_frequency() -> Dict[str, Any]:
        """Get current CPU frequency in MHz."""
        freq = psutil.cpu_freq()
        return {
            "value": round(freq.current, 2),
            "unit": "MHz",
            "type": "dynamic",
            "description": "Current CPU frequency"
        }
```

### Points clés d'implémentation

- **Intervalle bloquant :** fenêtre de mesure d'1 seconde pour un delta précis
- **Précision :** un chiffre après la virgule pour équilibrer précision et lisibilité
- **Métadonnées :** chaque métrique inclut unité, type et intervalle pour l'UI
- **Annotations de type :** améliorent la clarté et le support IDE

---

## Approfondissement : gestion de la mémoire

### Mémoire physique vs mémoire swap

SMO distingue deux types de mémoire critiques qui servent des objectifs fondamentalement différents dans le fonctionnement du système.

### Mémoire virtuelle (RAM physique)

**Définition :** Puces de RAM (mémoire à accès aléatoire) directement accessibles par le CPU

**Temps d'accès :** ~100 nanosecondes (extrêmement rapide)

**Cas d'usage :** Processus actifs, applications en cours, données fréquemment utilisées

**Technologie :** DRAM (RAM dynamique) — mémoire volatile

```python
# Implementation from metrics/memory.py
import psutil

def get_virtual_memory():
    """Collect virtual (physical) memory statistics."""
    vmem = psutil.virtual_memory()
    return {
        "total": vmem.total,          # Total physical RAM installed
        "available": vmem.available,  # RAM available for new processes
        "used": vmem.used,            # RAM actively in use
        "percent": vmem.percent,      # Usage percentage
        "buffers": vmem.buffers,      # OS buffer cache
        "cached": vmem.cached         # Page cache for file I/O
    }

# Example output:
# {
#     "total": 16777216000,        # 16 GB
#     "available": 8388608000,     # 8 GB available
#     "used": 7516192768,          # ~7 GB in use
#     "percent": 44.8,
#     "buffers": 209715200,        # 200 MB
#     "cached": 3221225472         # 3 GB
# }
```

### Mémoire swap (extension de la mémoire virtuelle)

**Définition :** Espace disque dédié au débordement mémoire lorsque la RAM est saturée

**Temps d'accès :** ~10 millisecondes (≈100 000× plus lent que la RAM)

**Cas d'usage :** Pages de mémoire inactives évincées par le noyau

**Technologie :** Partition/fichier sur SSD ou HDD

```python
def get_swap_memory():
    """Collect swap memory statistics."""
    swap = psutil.swap_memory()
    return {
        "total": swap.total,    # Swap partition/file size
        "used": swap.used,      # Bytes written to swap
        "free": swap.free,      # Available swap space
        "percent": swap.percent # Swap usage percentage
    }
```

### Comparaison technique

| Aspect | Mémoire physique | Mémoire swap |
|--------|------------------|--------------|
| Support | Puces DRAM | Partition SSD/HDD |
| Vitesse | 10–100 Go/s | 200–500 Mo/s (SSD) |
| Source noyau | /proc/meminfo | /proc/swaps |
| Seuil critique | >90 % = risque OOM | >50 % = thrashing |

### Justification de la supervision

Une utilisation élevée du swap indique une **pression mémoire** (RAM insuffisante), causant une forte dégradation via les E/S disque. Le système d'alertes de SMO déclenche des avertissements à des seuils configurables pour prévenir les ralentissements.

---

## Défis & solutions

### Défi 1 : erreurs de permissions

#### Problème

L'accès à certains fichiers `/proc` (notamment les informations au niveau des processus) nécessite des privilèges élevés. L'exécution en tant qu'utilisateur non root provoque des exceptions `PermissionError` ou `AccessDenied`.

```
psutil.AccessDenied: (pid=1234)
  Fichier "/proc/1234/stat" nécessite des privilèges root
```

#### Solution : dégradation maîtrisée

```python
import psutil
import logging

def collect_process_metrics(pid: int):
    """
    Collect process-level metrics with error handling.
    Falls back gracefully when permissions are insufficient.
    """
    try:
        process = psutil.Process(pid)
        return {
            "cpu_percent": process.cpu_percent(),
            "memory_info": process.memory_info(),
            "status": process.status()
        }
    except psutil.AccessDenied:
        logging.warning(f"Accès refusé pour le PID {pid}")
        return None  # Ignorer ce processus, continuer la supervision
    except psutil.NoSuchProcess:
        logging.debug(f"Le processus {pid} n'existe plus")
        return None
```

**Résultat :** L'agent continue son exécution avec moins de détails au niveau des processus, sans planter. Les métriques globales du système restent accessibles.

### Défi 2 : synchronisation des fréquences de rafraîchissement

#### Problème

Différentes métriques ont des fréquences idéales de collecte :

- CPU : 2 secondes (variations rapides)
- Disque : 10 secondes (variations lentes, requêtes coûteuses)
- Mémoire : 5 secondes (variations modérées)

Une approche monothread crée un timing rigide et sous-optimal.

#### Solution : mises à jour multi-threads

```python
import threading
import time

class MetricUpdater(threading.Thread):
    """Independent thread for metric collection."""
    
    def __init__(self, metric_fn, interval):
        super().__init__(daemon=True)
        self.metric_fn = metric_fn
        self.interval = interval
        self.running = True
        
    def run(self):
        """Collection loop with configurable interval."""
        while self.running:
            try:
                self.metric_fn()
            except Exception as e:
                logging.error(f"Metric collection error: {e}")
            time.sleep(self.interval)

# Lancer des threads indépendants avec intervalles optimisés
cpu_updater = MetricUpdater(collect_cpu, interval=2)
disk_updater = MetricUpdater(collect_disk, interval=10)
memory_updater = MetricUpdater(collect_memory, interval=5)

cpu_updater.start()
disk_updater.start()
memory_updater.start()
```

**Résultat :** Chaque collecteur fonctionne indépendamment avec un timing adapté, minimisant la charge système et maximisant la fraîcheur des données.

### Défi 3 : obsolescence des données du tableau de bord web

#### Problème

Les clients WebSocket se connectant quand le fichier de logs est vide ou très ancien reçoivent « Pas de données » indéfiniment.

#### Solution : suivi de fin de fichier avec relance

Le tableau de bord lit la **dernière ligne** du fichier JSONL et la diffuse via WebSocket. Si le fichier est vide, un état de chargement s'affiche avec une logique de relance automatique.

---

## Améliorations futures & conclusion

### Feuille de route v2.0

#### 1. Intégration GUI

- Native desktop application using PyQt or Tkinter
- System tray integration with notification badges
- Real-time graphs and charts for metric visualization
- Interactive configuration editor

#### 2. Intégration base de données

- Migrate from JSONL to TimeSeries Database (InfluxDB, Prometheus)
- Enable long-term metric retention (months/years)
- Implement efficient querying for historical analysis
- Support for downsampling and data aggregation

#### 3. Analytique avancée

- Machine learning anomaly detection (Isolation Forests, LSTM)
- Predictive capacity planning using time-series forecasting
- Automated performance bottleneck identification
- Correlation analysis between different metrics

#### 4. Supervision distribuée

- Agent-server architecture for multi-host monitoring
- Centralized dashboard aggregating metrics from multiple systems
- Service discovery integration (Consul, etcd, Kubernetes)
- Load balancing and high availability

#### 5. Alertes améliorées

- Webhook integrations (Slack, Discord, Microsoft Teams, PagerDuty)
- Complex alert rules: "CPU > 80% for > 5 consecutive minutes"
- Alert acknowledgment and escalation workflows
- SMS and email notification support

#### 6. Renforcement de la sécurité

- TLS/SSL for web dashboard (HTTPS with Let's Encrypt)
- Authentication middleware (OAuth2, JWT tokens, SAML)
- Role-based access control (RBAC) for multi-user environments
- Audit logging for security compliance

### Conclusion

**SMO** démontre une approche prête pour la production de supervision des ressources système en :

- ✓ Tirant parti de l'écosystème Python pour un développement rapide et fiable
- ✓ Implémentant une architecture modulaire garantissant la maintenabilité
- ✓ Proposant plusieurs interfaces (CLI, TUI, Web) pour divers usages
- ✓ Résolvant des défis concrets (permissions, threading, données obsolètes)
- ✓ Établissant une base solide pour des fonctionnalités « enterprise »

### Points clés à retenir

**« Une supervision efficace exige un juste équilibre entre profondeur technique, expérience utilisateur et fiabilité opérationnelle. »**

---

**Merci pour votre attention !**

**Des questions ?**
