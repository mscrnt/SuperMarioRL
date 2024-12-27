// path: static/js/base.js

// Initialize header controls for training and rendering
function initializeHeaderControls() {
    const startButton = document.getElementById("start-training");
    const stopButton = document.getElementById("stop-training");
    const statusText = document.getElementById("status");
    const videoPlaceholder = document.getElementById("video-placeholder");
    const videoFeed = document.getElementById("video-feed");

    // Check if the page has the required elements for training controls
    if (!startButton || !stopButton || !statusText) {
        console.warn("Header controls are not present on this page.");
        return;
    }

    const updateStatus = (isTraining, isRendering = false) => {
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

    const fetchTrainingStatus = async () => {
        try {
            const response = await fetch("/training/training_status");
            if (!response.ok) {
                throw new Error(`Failed to fetch training status: ${response.statusText}`);
            }
            const { training } = await response.json();
            updateStatus(training);
        } catch (error) {
            console.error("Error fetching training status:", error);
            updateStatus(false); // Default to "Stopped" on error
        }
    };

    const pollRenderStatus = async () => {
        if (!videoPlaceholder || !videoFeed) {
            return; // Skip polling if video elements are not present
        }

        try {
            const response = await fetch("/training/render_status");
            if (!response.ok) {
                throw new Error(`Failed to fetch render status: ${response.statusText}`);
            }
            const { rendering } = await response.json();
            updateStatus(true, rendering); // Update rendering status
            if (rendering) return; // Stop polling if rendering is active
        } catch (error) {
            console.error("Error polling render status:", error);
        }
        setTimeout(pollRenderStatus, 3000); // Poll every 3 seconds
    };

    startButton.onclick = async () => {
        try {
            const response = await fetch("/training/start_training", { method: "POST" });
            const result = await response.json();
            alert(result.message || "Training started successfully!");
            updateStatus(true); // Set "Running" but rendering might not be active yet
            pollRenderStatus(); // Start polling for rendering status
        } catch (error) {
            console.error("Error starting training:", error);
            alert("Failed to start training.");
        }
    };

    stopButton.onclick = async () => {
        try {
            const response = await fetch("/training/stop_training", { method: "POST" });
            const result = await response.json();
            alert(result.message || "Training stopped successfully!");
            updateStatus(false); // Update to "Stopped"
        } catch (error) {
            console.error("Error stopping training:", error);
            alert("Failed to stop training.");
        }
    };

    // Fetch training status on page load
    fetchTrainingStatus();
}

// Initialize base JavaScript
document.addEventListener("DOMContentLoaded", () => {
    initializeHeaderControls();
});
