<div align="center">

# ♊ Gemini Trading Agent

**AI-Powered, Web-Based, Self-Hosted Crypto Trading Bot**

[GitHub Repo](https://github.com/MembaCo/Gemini-Agent-Web) | [Setup](#setup-and-running) | [Features](#core-features)

[![Shield: License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Shield: Contributions Welcome](https://img.shields.io/badge/Contributions-Welcome-limegreen.svg)](#contributing)
[![Shield: Python](https://img.shields.io/badge/Python-3.11-3776AB.svg?logo=python)](https://www.python.org)
[![Shield: React](https://img.shields.io/badge/React-19-61DAFB.svg?logo=react)](https://react.dev/)

</div>

**Gemini Trading Agent** is a modern bot that performs advanced analysis and trading in crypto markets (Futures & Spot) using Google's powerful Gemini AI models, which you can run entirely on your own server.

Thanks to its user-friendly and modern web interface, you can easily manage all your operations, track your performance in real-time, backtest strategies, and quickly update bot settings.

<div align="center">

><img src="./screenshots/gallery-1.png" width="500" alt="Image of a showing the App">
><img src="./screenshots/gallery-2.png" width="500" alt="Image of a showing the App">
><img src="./screenshots/gallery-3.png" width="500" alt="Image of a showing the App">

</div>

## Why Gemini Trading Agent?

This project is designed for users with the following goals:

- 🏦 **Automation:** Automate trading strategies with a 24/7 system.
- 🧠 **AI Advantage:** Gain market edge with Google Gemini's advanced analysis capabilities.
- 🎯 **Data-Driven Decisions:** Trade based on technical indicators and AI analysis instead of emotional decisions.
- 👻 **Data Privacy:** Keep all strategy, settings, and transaction data on your own server (self-hosted).
- ⚙️ **Flexible Control:** Instantly modify all risk management and strategy parameters through the web interface.
- 📈 **Strategy Development:** Test different ideas risk-free on historical data with the backtest engine.

## ✨ Core Features

- ✅ **Web-Based Dashboard:** Fast and responsive interface developed with React for real-time P&L tracking, interactive charts, and live event flow.
- ✅ **Advanced Risk Management:**
    - **Dynamic Position Sizing:** Risks a specific percentage of capital in each trade.
    - **Smart Loss Reduction (Bailout Exit):** Minimizes losses by closing losing positions with AI confirmation during bottom recovery moments.
    - **Trailing Stop-Loss** and **Partial Take Profit**.
- ✅ **AI-Powered Analysis:**
    - In-depth market analysis with **Google Gemini 1.5 Flash/Pro**.
    - **Dominant Signal Analysis:** Enables more consistent decisions by informing AI about the strongly trending period in multi-timeframe analyses.
- ✅ **Smart Opportunity Scanner:**
    - Pre-screens potential trading opportunities with advanced filters like **volatility (ATR)** and **volume**.
    - Reduces costs by sending only promising candidates to AI analysis.
- ✅ **Strategy Backtest Engine:** Used to measure strategy performance under different market conditions.
- ✅ **Dynamic and Database-Driven Settings:** All bot settings can be updated instantly from the interface and stored permanently.
- ✅ **Telegram Integration:** Telegram support for instant notifications and basic bot commands.

## 🛠️ Technology Stack

| Layer | Technology |
| :--- | :--- |
| **Backend** | Python, FastAPI, LangChain, CCXT, Pandas-TA, APScheduler, asyncio |
| **Frontend** | React, Vite, Tailwind CSS, Chart.js, Lightweight Charts |
| **Database** | SQLite |
| **Deployment** | Docker, Docker Compose |

## 🚀 Setup and Running

**You must have [Git](https://git-scm.com/) and [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed on your computer to start.**

### 1. Clone the Project

```bash
git clone https://github.com/MembaCo/Gemini-Agent-Web.git
cd Gemini-Agent-Web
```

### 2. Configure Environment Variables
Create a new .env file by copying .env.example in the backend/ directory:

```bash
cp backend/.env.example backend/.env
```

Open the created .env file with a text editor and fill in the REQUIRED fields:

```bash
# REQUIRED SETTINGS
BINANCE_API_KEY="YOUR_BINANCE_API_KEY"
BINANCE_SECRET_KEY="YOUR_BINANCE_SECRET_KEY"
GOOGLE_API_KEY="YOUR_GOOGLE_AI_API_KEY"
ADMIN_USERNAME="admin"
ADMIN_PASSWORD_HASH="$2b$12$....YOUR_GENERATED_PASSWORD_HASH_HERE...."
SECRET_KEY="your_super_secret_key_for_jwt_tokens"

# OPTIONAL SETTINGS
TELEGRAM_ENABLED=True
TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID="YOUR_TELEGRAM_CHAT_ID"
USE_TESTNET=False
```

**Important: To generate a secure password hash, run the following command in the project's root directory and paste the output into the .env file:**

```bash
python3 backend/hash_password.py 'your_secure_password'
```

### 3. Start the Application
Run the following command while in the project's root directory:

```bash
docker-compose up --build
```

## 🖥️ Usage
After the application starts successfully, go to http://localhost:8080 in your browser.

Log in with the username and password you set in the .env file.

Monitor the bot, perform manual analysis, or start backtest operations from the Dashboard.

You can instantly change all bot settings from the Settings (⚙️) icon in the top right.

## 📂 Project Structure
```
Gemini-Agent-Web/
├── backend/        # Python FastAPI server and bot logic
│   ├── api/        # API endpoints
│   ├── core/       # Agent, strategy, position management
│   ├── tools/      # Exchange connection, indicator calculation etc.
│   ├── database/   # Database functions
│   └── .env        # Environment variables file
├── frontend/       # React-based web interface
├── data/          # Persistent data (e.g., trades.db SQLite)
├── docker-compose.yml
└── README.md
```

## ⚠️ Risk Warning
Warning: This software is developed for trading in financial markets. Crypto trading involves high risk and may result in the loss of some or all of your capital. Analyses or trades made by the software are not investment advice. All responsibility lies with the user. Make sure you understand the risks before opening live trades.

## 🤝 Contributing
Want to contribute? You can open an issue or submit a pull request. We're open to all suggestions and improvements!

## 📄 License
This project is licensed under the MIT License. See the LICENSE file for details.