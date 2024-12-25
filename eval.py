from stable_baselines3 import PPO
from gui import create_env, render_frame
from log_manager import LogManager
import torch
import cv2
import os
import glob

# Initialize logger
logger = LogManager("eval").get_logger_instance()

def get_newest_model(directory, extension="*.zip"):
    """
    Finds the newest file with the specified extension in the given directory.
    :param directory: Path to the directory containing the files.
    :param extension: File extension to search for (default is "*.zip").
    :return: Path to the newest file or None if no files are found.
    """
    files = glob.glob(os.path.join(directory, extension))
    if not files:
        logger.error(f"No files found with extension {extension} in directory: {directory}")
        return None
    newest_file = max(files, key=os.path.getmtime)
    logger.info(f"Newest model found: {newest_file}")
    return newest_file

def evaluate_model(model_path, num_episodes=5):
    """
    Evaluates a trained PPO model by running it in the environment.
    :param model_path: Path to the trained model file.
    :param num_episodes: Number of episodes to evaluate.
    """
    if not model_path:
        logger.error("No model provided for evaluation.")
        return

    logger.info(f"Loading model from {model_path}...")
    model = PPO.load(model_path)

    logger.info("Creating evaluation environment...")
    eval_env = create_env()()  # Single environment for evaluation

    for episode in range(1, num_episodes + 1):
        logger.info(f"Starting Episode {episode}...")
        obs = eval_env.reset()
        done = False
        total_reward = 0

        while not done:
            # Predict action from model
            action, _ = model.predict(obs, deterministic=True)

            # Perform action in the environment
            obs, reward, done, info = eval_env.step(action)
            total_reward += reward

            # Render the frame
            render_frame(eval_env, timestep=int(total_reward))

        logger.info(f"Episode {episode} finished. Total Reward: {total_reward}")

    eval_env.close()
    logger.info("Evaluation completed.")
    cv2.destroyAllWindows()


if __name__ == "__main__":
    # Directory containing the checkpoints
    checkpoints_dir = "./checkpoints"

    # Automatically get the newest model file
    trained_model_path = get_newest_model(checkpoints_dir)

    # Run the evaluation
    evaluate_model(trained_model_path)
