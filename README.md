# Darts in the Dungeon 🎯

A sleek, modern, and responsive web-based darts scorer application built with Flask and vanilla JavaScript. Perfect for tracking your games of X01 and Around the World, whether you're playing solo or in teams.

<p align="center">
  <img src="images/darts.png" alt="Darts Scorer Screenshot" width="60%">
</p>


## ✨ Features

*   **Multiple Game Modes**: Play standard `501`, `301`, etc., or the classic `Around the World`.
*   **Teams & Solo Play**: Supports standard 1v1 play and a 2v2 teams mode with correct player rotation.
*   **Real-time UI**: The interface updates instantly with every throw, showing scores, turn history, and active player highlights.
*   **Checkout Suggestions**: For X01 games, the app provides common two and three-dart checkout combinations for scores of 170 and under.
*   **Full Turn History**: A scrollable log keeps track of every completed turn.
*   **Undo Functionality**: Made a mistake? Easily undo the last throw.
*   **Game Statistics**: View a summary of player performance, including 3-dart average and total darts thrown.
*   **Editable Player Names**: Customize player names on the fly.

## 🛠️ Tech Stack

*   **Backend**: Python with Flask
*   **Frontend**: HTML, Tailwind CSS, and Vanilla JavaScript
*   **WSGI Server**: Gunicorn (for Docker deployment)
*   **Package Manager**: uv

## 🚀 Local Development Setup

To run the application on your local machine:

1.  **Clone the repository:**
    ```sh
    git clone https://github.com/scottastone/darts
    cd darts
    ```

2.  **Create a virtual environment and install dependencies:**
    This project uses `uv` for package management.
    ```sh
    # Create the virtual environment
    uv venv

    # Activate it (on Linux/macOS)
    source .venv/bin/activate

    # Install dependencies
    uv pip install -r requirements.txt
    ```

3.  **Run the Flask development server:**
    ```sh
    python app.py
    ```

4.  Open your browser and navigate to `http://127.0.0.1:5054`.

## 🐳 Docker Deployment

Deploying the application with Docker is the recommended method for a production-like environment.

### Prerequisites
*   Docker
*   Docker Compose

### Steps

1.  **Build and run the container using Docker Compose:**
    From the root of the project directory, run the following command:
    ```sh
    docker compose up -d --build
    ```
    This command will:
    *   Build the Docker image as defined in the `Dockerfile`.
    *   Start a container from that image.
    *   Forward port 5054 on your host machine to the container.

2.  **Access the application:**
    Once the container is running, open your browser and navigate to `http://localhost:5054`.

3.  **To stop the application:**
    Press `Ctrl+C` in the terminal where `docker-compose` is running, then run:
    ```sh
    docker compose down
    ```

## 📝 API Endpoints

The application is a single-page app that communicates with a Flask backend via a simple REST API.

*   `GET /api/state`: Retrieves the current game state.
*   `POST /api/score`: Records a new throw.
*   `POST /api/undo`: Reverts the last throw.
*   `POST /api/reset`: Starts a new game with a specified mode.
*   `POST /api/names`: Updates player names.
*   `POST /api/settings`: Toggles game settings like Teams Mode.
*   `GET /api/stats`: Calculates and returns game statistics.