# 🚌 ITLA Bus Bot

> Bot de Discord que automatiza la reserva y compra de boletos del sistema de transporte del **Instituto Tecnológico de Las Américas (ITLA)**, pensado para estudiantes que viajan en las mismas rutas y paradas cada semana.

---

## ✨ ¿Qué hace?

1. Te registras con tus credenciales del campus virtual del ITLA.
2. Configuras tu horario semanal de rutas (días, paradas, horas de llegada y salida).
3. El bot te notifica **un día antes** de cada clase presencial y te pregunta si deseas comprar los boletos.
4. Si confirmas, el bot realiza la reserva y compra automáticamente mediante web scraping y **te envía los boletos directamente al chat de Discord**.

---

## 🗂️ Estructura del proyecto

```
app/
├── bot/
│   ├── cogs/          # Comandos y eventos del bot (slash commands)
│   ├── ui/            # Componentes de interfaz (modals, selects, botones)
│   ├── utils/         # Utilidades del bot
│   └── bot_discord.py # Entrada principal del bot
├── data/              # Almacenamiento local / archivos de datos
├── infrastructure/
│   ├── repository/    # Capa de acceso a datos
│   ├── database.py    # Configuración de la base de datos
│   └── models.py      # Modelos ORM / esquemas
├── models/            # Modelos de dominio / lógica de negocio
├── scraper/           # Web scraping con Playwright
└── main.py            # Punto de entrada de la aplicación
.env.example           # Variables de entorno de ejemplo
pyproject.toml         # Configuración del proyecto (UV)
uv.lock                # Lock file de dependencias
```

---

## ⚙️ Requisitos previos

- **Python 3.11+**
- **[UV](https://docs.astral.sh/uv/)** — gestor de proyectos y entornos virtuales
- Un **bot de Discord** creado en el [Discord Developer Portal](https://discord.com/developers/applications) con los intents necesarios habilitados

---

## 🚀 Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/itla-bus-bot.git
cd itla-bus-bot
```

### 2. Instalar UV (si no lo tienes)

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 3. Instalar las dependencias del proyecto

```bash
uv sync
```

> Esto crea automáticamente el entorno virtual e instala todas las dependencias definidas en `pyproject.toml`.

### 4. Instalar los navegadores de Playwright

```bash
uv run playwright install chromium
```

---

## 🔐 Variables de entorno

Copia el archivo de ejemplo y completa los valores:

```bash
cp .env.example .env
```

Edita el archivo `.env`:

```env
# Token del bot de Discord (obtenido en el Developer Portal)
DISCORD_TOKEN=tu_token_aqui
```

---

## ▶️ Ejecutar el bot

```bash
uv run python app/main.py
```

---

## 💬 Comandos del bot

### `/register`

Registra tu cuenta con las credenciales del **campus virtual del ITLA**.

- Utilizara los parametros del comando para agregar tu **correo** y **contraseña**.
- Las credenciales se almacenan de forma segura para realizar las reservas automáticas.

---

### `/set-schedule`

Configura tu horario de rutas del ITLA **por cuatrimestre**.

El horario que defines representa los días fijos de la semana (lunes a sábado) en que asistirás presencialmente durante ese cuatrimestre. El bot usará esta configuración para saber cuándo enviarte las notificaciones de compra.

El flujo es el siguiente:

1. **Modal de cuatrimestre** — Ingresa el cuatrimestre en que te encuentras (ej: `2026-1`).
2. **Selección de días** — Elige qué días de la semana asistirás al ITLA durante ese cuatrimestre (lunes a sábado).
3. **Configuración por día** — Para cada día seleccionado, defines mediante menús desplegables:
   | Campo | Descripción |
   |---|---|
   | 🕐 Hora de llegada | Hora a la que llegarás al ITLA |
   | 📍 Parada de recogida | Parada donde el bus te recogerá |
   | 🕔 Hora de salida | Hora a la que saldrás del ITLA |

---

## 🔄 Flujo completo

```
Usuario                          Bot
  │                               │
  ├──/register──────────────────► │  Guarda credenciales del campus virtual
  │                               │
  ├──/set-schedule───────────────►│  Configura horario del cuatrimestre
  │                               │
  │     (11:00 AM, día anterior)  │
  │◄── "¿Deseas comprar tus  ─────┤  Notificación automática
  │     boletos para mañana?"     │
  │                               │
  ├──── ✅ Sí ───────────────────►│  Realiza reserva y compra con Playwright
  │                               │
  │◄── 🎫 [Boletos adjuntos] ─────┤  Envía los boletos al chat
```

> 🕙 **Hora de notificación:** el bot envía el recordatorio cada mañana a las **11:00 AM**, un día antes de cada clase presencial programada en tu horario.
> Para cambiar la hora, edita el archivo `app/bot/cogs/scheduler_task_cog.py`.

---

## 🛠️ Tecnologías utilizadas

| Tecnología | Uso |
|---|---|
| [discord.py](https://discordpy.readthedocs.io/) | Framework del bot de Discord |
| [Playwright](https://playwright.dev/python/) | Web scraping y automatización del portal ITLA |
| [UV](https://docs.astral.sh/uv/) | Gestión de entorno y dependencias |
| Python 3.11+ | Lenguaje principal |

---

## 📄 Licencia

Este proyecto está bajo la licencia especificada en el archivo [LICENSE](./LICENSE).

---

> Desarrollado para facilitar la vida de los estudiantes del ITLA 🎓
