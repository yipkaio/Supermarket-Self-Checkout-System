<div align="center">

# 🛒 Supermarket Self-Checkout System

**An AIoT self-checkout kiosk on Raspberry Pi, with an online store and an admin dashboard that share one live product database.**

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)
![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![Vite](https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-A22846?style=for-the-badge&logo=raspberrypi&logoColor=white)

*ET0735 DevOps for AIoT · Singapore Polytechnic · Jan – Feb 2026*

</div>

---

## 📖 Overview

A self-checkout system for a fictional supermarket, **SPmart**, built to cut down queue times. Customers can scan and pay at an in-store kiosk, or shop online and choose store pickup or home delivery. Staff manage products from a web dashboard, and every change shows up immediately on the kiosk and the online store.

<div align="center">
<img src="Images/System.png" alt="System architecture" width="720">
</div>

---

## ✨ Features

| 🏪 In-store kiosk (Raspberry Pi) | 🌐 Online store | 🛠️ Admin dashboard |
|---|---|---|
| Camera barcode scanning | Browse products and add to cart | Secure staff login |
| LCD shows item, price and running total | Store pickup with QR code | Create, edit and delete products |
| Keypad menu navigation | Home delivery (+$4.00) with address | Product image uploads |
| ATM PIN payment via keypad | User registration | Search and stock management |
| RFID PayWave payment | PayNow QR payment | Barcode lookup API |
| QR scan to collect online orders | | Dockerised for deployment |

---

## 🏗️ Architecture

```
┌──────────────────────┐   ┌──────────────────────┐   ┌──────────────────────┐
│   In-store kiosk     │   │    Online store      │   │   Admin dashboard    │
│  Raspberry Pi + HAL  │   │  React + Flask API   │   │  React + Flask API   │
│ camera · LCD · keypad│   │                      │   │  (Docker + Nginx)    │
│       RFID           │   │                      │   │                      │
└──────────┬───────────┘   └──────────┬───────────┘   └──────────┬───────────┘
           │                          │                          │
           └──────────────────────────┼──────────────────────────┘
                                      ▼
                        ┌───────────────────────────┐
                        │   MySQL database (cloud)  │
                        │ products · transactions · │
                        │   transaction_items ·     │
                        │          users            │
                        └───────────────────────────┘
```

<details>
<summary><b>More diagrams</b></summary>

<br>

**Application layer**
<img src="Images/Application.png" alt="Application layer" width="720">

**Hardware layer**
<img src="Images/Hardware.png" alt="Hardware layer" width="720">

**Use cases**
<img src="Images/Usecase.png" alt="Use case diagram" width="720">

**In-store purchase flow**
<img src="Images/Instore.png" alt="In-store flow chart" width="720">

**Overall system flow**
<img src="Images/Generalflow.png" alt="General flow chart" width="720">

</details>

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| Kiosk | Python, Raspberry Pi, Picamera2, OpenCV, pyzbar, course HAL library |
| Web frontends | React 19, Vite, Lucide icons |
| Backend APIs | Flask, Flask-CORS |
| Database | MySQL (hosted on Railway) |
| Deployment | Docker, Docker Compose, Nginx |
| Testing | pytest |

---

## 📁 Project Structure

```
├── src/                 # In-store kiosk (Raspberry Pi)
│   ├── main.py          # Checkout flow, payments, QR pickup
│   ├── menu.py          # Keypad/LCD menu navigation
│   ├── barcode_scanner.py
│   └── hal/             # Hardware abstraction layer (course submodule)
├── admin-app/           # Staff dashboard
│   ├── src/             # React frontend
│   ├── backend/         # Flask REST API
│   ├── Dockerfile       # Frontend build served by Nginx
│   └── docker-compose.yml
├── user-app/            # Customer online store
│   ├── src/             # React frontend
│   └── backend/         # Flask API (checkout, register, pickup QR)
├── Product_Barcodes/    # Printable barcodes for demo products
├── tests/               # pytest suites for menu and LCD
├── Images/              # Diagrams used in this README
└── docs/                # SRS, sprint planning, test report
```

---

## 🚀 Getting Started

### Database
All three apps read their connection details from environment variables:

```bash
DB_HOST=your-host
DB_PORT=3306
DB_USER=your-user
DB_PASSWORD=your-password
DB_NAME=your-database
```

### Admin dashboard (Docker)
```bash
cd admin-app
docker compose up -d
```
Open `http://<Raspberry_Pi_IP>` in a browser on the same Wi-Fi network as the Pi.

### Customer store
```bash
cd user-app
npm install && npm run dev       # frontend
python backend/app.py            # backend
```

### In-store kiosk
Runs on a Raspberry Pi with the course HAL board (camera, LCD, keypad, RFID reader).
```bash
cd src
python main.py
```

### Tests
```bash
pytest tests/
```

---

## 🗄️ Data Model

| Table | Key fields |
|---|---|
| `products` | product_id, barcode (10-digit), name, price, stock, image |
| `transactions` | transaction_id, user_id, total, created_at |
| `transaction_items` | transaction_id, product_id, quantity, price_at_purchase |
| `users` | user_id, username, password, address |

---

## 👨‍💻 My Contributions — Yip Kai

I was the repository maintainer and built the data and admin side of the system:

- **Database design.** Designed the MySQL schema, then iterated from a first version with inventory counting to a second version with delete support.
- **Admin dashboard.** Built the React + Flask app end to end: staff login, a REST API for product CRUD, image uploads, search and stock management, and a barcode lookup endpoint used by the kiosk.
- **Product barcodes.** Assigned 10-digit barcode IDs and generated printable barcode images for the demo products.
- **Kiosk navigation.** Reworked the in-store flow so customers can go back between steps.
- **Docker deployment.** Containerised the admin app with a multi-stage build served by Nginx, plus Docker Compose.
- **Documentation and repo management.** Wrote the project documentation and diagrams, and reviewed and merged pull requests from the team.

---

## 🤝 Team

| Member | Main contributions |
|---|---|
| **Yip Kai** | Database, admin dashboard, Docker, documentation |
| **Moses Kong** | Kiosk menu navigation, camera barcode scanning, QR pickup verification, RFID PayWave, pytest suites |
| **Yap Jun Xiang** | Customer online store, pickup and PayNow QR generation, delivery address checkout |

Hardware abstraction layer and project template provided by the ET0735 teaching team.

---

## 🔮 Future Improvements

- Loyalty rewards and mobile wallet support
- AI-based product recognition instead of barcodes
- Digital receipts
- Multi-language interface
