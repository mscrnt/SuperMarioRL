// path: static/js/base.js

// Initialize header controls for training and rendering
function initializeHeaderControls() {
    const startButton = document.getElementById("start-training");
    const stopButton = document.getElementById("stop-training");
    const statusText = document.getElementById("status");
    const videoPlaceholder = document.getElementById("video-placeholder");
    const videoFeed = document.getElementById("video-feed");

    if (!startButton || !stopButton || !statusText || !videoPlaceholder || !videoFeed) {
        console.error("Header controls or video elements are missing in the DOM.");
        return;
    }

    const updateStatus = (isTraining, isRendering) => {
        statusText.textContent = isTraining ? "Running" : "Stopped";
        statusText.style.color = isTraining ? "#28a745" : "#007BFF"; // Green for Running, Blue for Stopped
        startButton.disabled = isTraining;
        stopButton.disabled = !isTraining;

        // Update video feed visibility only if video elements are present
        if (videoPlaceholder && videoFeed) {
            videoPlaceholder.style.display = isRendering ? "none" : "block";
            videoFeed.style.display = isRendering ? "block" : "none";
        }

        // Update the document title
        document.title = isTraining ? "Training in Progress" : "Training Stopped";
    };

    startButton.onclick = async () => {
        try {
            // Collect configurations from the UI
            const config = {
                training_config: {},
                hyperparameters: {},
                wrappers: [], // Changed to match what backend expects
                callbacks: [] // Changed to match what backend expects
            };
    
            // Extract training configurations
            document.querySelectorAll(".config-input").forEach((input) => {
                const name = input.name;
                const value = input.value;
                if (name.startsWith("hyperparameters")) {
                    config.hyperparameters[name.split("[")[1].replace("]", "")] = value;
                } else if (name.startsWith("training_config")) {
                    config.training_config[name.split("[")[1].replace("]", "")] = value;
                }
            });
    
            // Extract enabled wrappers
            document.querySelectorAll(".wrapper-checkbox:checked").forEach((checkbox) => {
                config.wrappers.push(checkbox.value); // Use checkbox.value, not dataset.key
            });
    
            // Extract enabled callbacks
            document.querySelectorAll(".callback-checkbox:checked").forEach((checkbox) => {
                config.callbacks.push(checkbox.value); // Use checkbox.value, not dataset.key
            });
    
            // Send the configuration to the backend
            const response = await fetch("/training/start_training", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(config) // Pass the collected configuration
            });
    
            const result = await response.json();
            alert(result.message || "Training started successfully!");
            updateStatus(true, false); // Training started but rendering not yet active
            pollRenderStatus(); // Start polling for rendering status
        } catch (error) {
            console.error("Error starting training:", error);
            alert("Failed to start training.");
        }
    };
    
    

    stopButton.onclick = async () => {
        try {
            const response = await fetch("/training/stop_training", { method: "POST" }); // Adjusted route
            const result = await response.json();
            alert(result.message || "Training stopped successfully!");
            updateStatus(false, false); // Training stopped, so rendering also stops
        } catch (error) {
            console.error("Error stopping training:", error);
            alert("Failed to stop training.");
        }
    };

    const pollRenderStatus = async () => {
        try {
            const response = await fetch("/training/render_status"); // Adjusted route
            const { rendering } = await response.json();
            updateStatus(true, rendering); // Update based on rendering status
            if (rendering) return; // Stop polling once rendering is active
        } catch (error) {
            console.error("Error polling render status:", error);
        }
        setTimeout(pollRenderStatus, 3000); // Poll every 3 seconds
    };

    const pollTrainingStatus = async () => {
        try {
            const response = await fetch("/training/training_status");
            const { training } = await response.json();
            updateStatus(training, false); // Assume rendering is off if training is stopped
        } catch (error) {
            console.error("Error polling training status:", error);
            updateStatus(false, false); // Default to "stopped" if there's an error
        }
    };
    
    // Initial status checks
    (async () => {
        updateStatus(false, false); // Default to "Stopped" before the first backend call
        await pollTrainingStatus();
    })();
}

// Initialize base JavaScript
document.addEventListener("DOMContentLoaded", () => {
    initializeHeaderControls();
});
