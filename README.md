# TNT Smart Scheduling App

## Project Overview

The TNT Smart Scheduling App is a comprehensive, intelligent scheduling and resource management system designed for university environments. It aims to streamline the process of booking, utilizing, and managing various campus resources, from academic services to recreational facilities. The project consists of a powerful backend built with FastAPI and a cross-platform mobile application developed using React Native.

## Problem Statement

University campuses are complex ecosystems with a high demand for shared resources. Students and faculty often face challenges in scheduling appointments, booking facilities, and managing their time effectively. Existing systems are often fragmented, inefficient, and lack real-time capabilities. This project addresses these issues by providing a centralized, user-friendly platform that optimizes resource allocation and enhances the overall campus experience.

## Features

-   **User Authentication:** Secure login and registration for students, faculty, and administrators.
-   **Smart Scheduling:** AI-powered scheduling for appointments, consultations, and study sessions.
-   **Resource Booking:** Real-time booking of campus facilities such as study rooms, labs, and sports courts.
-   **Order Management:** A complete system for placing and tracking orders for various campus services (e.g., stationery, food).
-   **Payment Integration:** Seamless and secure payment processing for all transactions.
-   **Real-time Notifications:** Instant alerts for appointment reminders, booking confirmations, and order status updates.
-   **Admin Dashboard:** A comprehensive dashboard for administrators to manage users, resources, and services.

## Technology Stack

### Backend

-   **Framework:** FastAPI
-   **Database:** PostgreSQL
-   **ORM:** SQLAlchemy with Alembic for migrations
-   **Authentication:** JWT (JSON Web Tokens)
-   **Testing:** Pytest
-   **Asynchronous Tasks:** (Not specified, e.g., Celery)

### Frontend

-   **Framework:** React Native
-   **Language:** TypeScript
-   **State Management:** (Not specified, e.g., Redux Toolkit)
-   **Navigation:** React Navigation
-   **UI Components:** (Not specified, e.g., React Native Paper)

## System Architecture

*A high-level diagram of the system architecture will be added here.*

## Installation Steps

### Prerequisites

-   Node.js and npm/yarn
-   Python 3.8+ and pip
-   PostgreSQL
-   Git

### Backend

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Jemin29/finalyear.git
    cd finalyear/tnt-backend-main
    ```
2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Set up the database:**
    -   Create a PostgreSQL database.
    -   Configure the database connection in a `.env` file (based on `.env.example`).
5.  **Run database migrations:**
    ```bash
    alembic upgrade head
    ```
6.  **Run the application:**
    ```bash
    uvicorn app.main:app --reload
    ```

### Frontend

1.  **Navigate to the frontend directory:**
    ```bash
    cd ../tnt-frontend
    ```
2.  **Install dependencies:**
    ```bash
    npm install
    ```
3.  **Run the application:**
    -   **For Android:** `npx react-native run-android`
    -   **For iOS:** `npx react-native run-ios`

## Folder Structure

```
finalyear/
├── tnt-backend-main/
│   ├── alembic/          # Database migrations
│   ├── app/              # Main application source code
│   ├── tests/            # Pytest test suite
│   ├── .venv/            # Python virtual environment
│   └── requirements.txt  # Python dependencies
└── tnt-frontend/
    ├── android/          # Android project
    ├── ios/              # iOS project
    ├── src/              # React Native source code
    ├── node_modules/     # Node.js dependencies
    └── package.json      # Project configuration
```

## Contributors

-   Jemin29
-   Jatinpatel321
