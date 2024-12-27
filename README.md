# Super Mario RL

Super Mario RL is a Reinforcement Learning (RL) framework designed to train RL agents in the Super Mario environment. This project combines the power of Stable Baselines3, dynamic wrappers and callbacks, and a Flask-based GUI for easy visualization and management.

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
├── checkpoints/                # Saved models during training
├── configs/                    # Configuration files for training setups
├── gui/                        # GUI-related Python files
├── logs/                       # Logs for training, debugging, and system events
├── routes/                     # Flask route blueprints
│   ├── config_routes.py        # Routes for managing configurations
│   ├── dashboard_routes.py     # Routes for the main dashboard
│   ├── stream_routes.py        # Routes for streaming logs and video
│   ├── tensorboard_routes.py   # Routes for TensorBoard management
│   └── training_routes.py      # Routes for managing training sessions
├── static/                     # Static files for CSS, JS, and other assets
│   ├── css/                    # Stylesheets
│   ├── js/                     # JavaScript logic
│   ├── json/                   # Tooltip data for the dashboard
│   ├── webfonts/               # Font assets
│   └── favicon.ico             # Favicon for the site
├── templates/                  # HTML templates for the Flask app
│   ├── base.html               # Base HTML layout
│   ├── index.html              # Main dashboard page
│   └── tensorboard.html        # TensorBoard integration page
├── .gitignore                  # Git ignore file
├── app_callbacks.py            # Definitions for training callbacks
├── app_wrappers.py             # Definitions for environment wrappers
├── app.py                      # Flask app entry point
├── eval.py                     # Evaluation script for trained models
├── global_state.py             # Shared global state for the app
├── log_manager.py              # Centralized logging utility
├── optuna.py                   # Hyperparameter tuning using Optuna
├── preprocessing.py            # Preprocessing utilities for observations
├── README.md                   # Project documentation
├── render_manager.py           # Utilities for rendering game frames
├── requirements.txt            # List of dependencies
├── train.py                    # Main training script
└── utils.py                    # Utility functions and helper classes
```

---

## Features

- **Dynamic Wrappers and Callbacks**: Modular wrapper and callback management using the `Blueprint` pattern.
- **Flask-based GUI**: Interactive web dashboard for controlling training and viewing real-time updates.
- **TensorBoard Integration**: Built-in visualization of training progress.
- **Advanced Logging**: Centralized logging with dynamic updates on the GUI.
- **Configurable Training**: Manage and reuse configurations through the GUI.
- **Hyperparameter Optimization**: Integrated Optuna support for fine-tuning.
- **Video Streaming**: Real-time rendering of gameplay on the dashboard.
- **Extensibility**: Easy addition of new wrappers, callbacks, and training logic.

---

## Installation

1. **Clone the Repository**:
   ```bash
   git clone <repository_url>
   cd <repository_name>
   ```

2. **Install Python Dependencies**:
   ```bash
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Run the Flask App**:
   ```bash
   python app.py
   ```

4. **Open in Browser**:
   Navigate to `http://127.0.0.1:5000` to access the GUI.

---

## Usage

### Training

1. Launch the Flask app and configure training through the GUI.
2. Start training and monitor logs, video streams, and TensorBoard.
3. Save and load configurations for reuse.

### Evaluation

Evaluate a trained model:
```bash
python eval.py --model_path checkpoints/model.zip
```

### Hyperparameter Optimization

Run Optuna:
```bash
python optuna.py
```

---

## Components

### Core Scripts

1. **`train.py`**: Training script with environment setup and dynamic wrapper/callback application.
2. **`eval.py`**: Evaluation script for assessing trained models.
3. **`optuna.py`**: Hyperparameter tuning using Optuna.
4. **`log_manager.py`**: Manages logging across all components.

### Wrappers

- Defined in `app_wrappers.py`.
- Extend or modify environment behavior.
- Examples: `EnhancedStatsWrapper`, `RewardManager`.

### Callbacks

- Defined in `app_callbacks.py`.
- Automate tasks during training.
- Examples: `AutoSave`, `RenderCallback`.

### GUI

1. **Frontend**:
   - CSS, JavaScript, and templates in `static/` and `templates/`.
2. **Backend**:
   - Flask blueprints in `routes/`.

---

## Contributing

1. Fork the repository.
2. Create a branch: `git checkout -b feature-name`.
3. Commit changes: `git commit -m "Add feature"`.
4. Push: `git push origin feature-name`.
5. Submit a pull request.

---

## License

This project is licensed under the MIT License.
```