# Super Mario RL

Super Mario RL is a Reinforcement Learning (RL) framework built to train RL agents on a Super Mario environment. This project provides a modular design to dynamically load and apply wrappers and callbacks, leveraging tools like Stable Baselines3, Optuna for optimization, and a Flask-based GUI for visualization and management.

---

## Table of Contents

- [Super Mario RL](#super-mario-rl)
  - [Table of Contents](#table-of-contents)
  - [Folder Structure](#folder-structure)
  - [Features](#features)
  - [Installation](#installation)
  - [Usage](#usage)
    - [Training](#training)
    - [Evaluation](#evaluation)
    - [Hyperparameter Optimization](#hyperparameter-optimization)
  - [Components](#components)
    - [Core Scripts](#core-scripts)
    - [Wrappers](#wrappers)
    - [Callbacks](#callbacks)
    - [GUI](#gui)
  - [Contributing](#contributing)
  - [License](#license)

---

## Folder Structure

```
project/
│
├── gui/
│   └── __init__.py               # Initialization for the GUI package
│
├── static/
│   ├── css/
│   │   └── style.css            # CSS for styling the Flask web interface
│   └── js/
│       └── script.js            # JavaScript for interactivity on the web interface
│
├── templates/
│   ├── base.html                # Base HTML layout for the Flask app
│   ├── index.html               # Main dashboard page for the web app
│   └── tensorboard.html         # TensorBoard page for visualizing training progress
│
├── app_callbacks.py             # Definitions for training callbacks
├── app_wrappers.py              # Definitions for environment wrappers
├── app.py                       # Flask-based GUI for managing training
├── eval.py                      # Evaluation script for trained models
├── log_manager.py               # Custom logging utilities
├── optuna.py                    # Optuna integration for hyperparameter tuning
├── preprocessing.py             # Preprocessing utilities for observations
├── render_manager.py            # Utilities for rendering game frames
├── requirements.txt             # List of dependencies
├── train.py                     # Main script for training the RL agent
└── utils.py                     # Utility functions and helper classes
```

---

## Features

- **Dynamic Wrappers and Callbacks**: Modular wrapper and callback management using `Blueprint` patterns.
- **Flask-based GUI**: Intuitive web-based interface for controlling training, monitoring logs, and updating configurations.
- **Optuna Integration**: Hyperparameter optimization using Optuna.
- **TensorBoard Integration**: Easy-to-use TensorBoard visualizations.
- **Subprocess Management**: Parallelized environment creation for efficient training.
- **Extensible**: Add new wrappers, callbacks, or training methods with ease.

---

## Installation

1. **Clone the Repository**:
   ```bash
   git clone <repository_url>
   cd <repository_name>
   ```

2. **Install Python Dependencies**:
   Create a virtual environment and install the requirements:
   ```bash
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Run Flask App**:
   Start the web app:
   ```bash
   python app.py
   ```

4. **Open in Browser**:
   Navigate to `http://127.0.0.1:5000` to access the interface.

---

## Usage

### Training

1. **Launch the Flask App**:
   ```bash
   python app.py
   ```

2. **Configure Training**:
   - Access the dashboard at `http://127.0.0.1:5000`.
   - Modify hyperparameters, training configurations, wrappers, and callbacks dynamically via the GUI.

3. **Start Training**:
   - Click the **Start Training** button on the dashboard.
   - Monitor logs and game renders in real time.

4. **Stop Training**:
   - Click the **Stop Training** button to gracefully stop training.

### Evaluation

Evaluate a trained model using the `eval.py` script:
```bash
python eval.py --model_path checkpoints/model.zip
```

### Hyperparameter Optimization

Run Optuna for hyperparameter tuning:
```bash
python optuna.py
```

---

## Components

### Core Scripts

1. **`train.py`**:
   - Main script for training the RL agent.
   - Handles environment setup, model initialization, and training loops.
   - Uses `create_env` from `utils.py` to dynamically wrap environments.

2. **`eval.py`**:
   - Script for evaluating trained models.
   - Loads a model and runs it in the game environment to measure performance.

3. **`optuna.py`**:
   - Script for hyperparameter optimization.
   - Uses Optuna to tune hyperparameters for better model performance.

4. **`log_manager.py`**:
   - Centralized logging utility for structured log management.

### Wrappers

- Defined in `app_wrappers.py`.
- Extend or modify environment behavior (e.g., `EnhancedStatsWrapper` adds custom statistics to observations).
- New wrappers can be added using the `Blueprint` system in `utils.py`.

### Callbacks

- Defined in `app_callbacks.py`.
- Automate tasks during training (e.g., saving models, stopping training).
- Use `Blueprint` to dynamically register and configure callbacks.

### GUI

1. **Frontend**:
   - **CSS**: `static/css/style.css` for styling.
   - **JavaScript**: `static/js/script.js` for interactivity.
   - **HTML Templates**: Defined in the `templates/` directory.

2. **Backend**:
   - Flask app in `app.py`.
   - Provides REST endpoints for training control, log streaming, and configuration updates.

---

## Contributing

1. Fork the repository.
2. Create a new branch: `git checkout -b feature-name`.
3. Commit your changes: `git commit -m "Add new feature"`.
4. Push to the branch: `git push origin feature-name`.
5. Submit a pull request.

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
