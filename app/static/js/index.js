// Initialize header controls for training and rendering
function initializeHeaderControls() {
    const startButton = document.getElementById("start-training");
    const stopButton = document.getElementById("stop-training");
    const statusText = document.getElementById("status");
    const videoPlaceholder = document.getElementById("video-placeholder");
    const videoFeed = document.getElementById("video-feed");

    if (!startButton || !stopButton || !statusText) {
        console.error("Header controls or status text are missing in the DOM.");
        return;
    }

    // Update the UI status
    const updateStatus = (isTraining, isRendering) => {
        statusText.textContent = isTraining ? "Running" : "Stopped";
        statusText.style.color = isTraining ? "#28a745" : "#007BFF"; // Green for Running, Blue for Stopped
        startButton.disabled = isTraining;
        stopButton.disabled = !isTraining;

        // Update video feed visibility if elements exist
        if (videoPlaceholder && videoFeed) {
            videoPlaceholder.style.display = isRendering ? "none" : "block";
            videoFeed.style.display = isRendering ? "block" : "none";
        }

        // Update the document title
        document.title = isTraining ? "Training in Progress" : "Training Stopped";
    };

    // Start training event
    startButton.onclick = async () => {
        try {
            const config = collectTrainingConfig();
            const response = await fetch("/training/start_training", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(config),
            });

            const result = await response.json();
            if (response.ok) {
                alert(result.message || "Training started successfully!");
                updateStatus(true, false);
                pollRenderStatus();
            } else {
                console.error(result.message);
                alert(`Error: ${result.message}`);
            }
        } catch (error) {
            console.error("Error starting training:", error);
            alert("Failed to start training.");
        }
    };

    // Stop training event
    stopButton.onclick = async () => {
        try {
            const response = await fetch("/training/stop_training", { method: "POST" });
            const result = await response.json();
            if (response.ok) {
                alert(result.message || "Training stopped successfully!");
                updateStatus(false, false);
            } else {
                console.error(result.message);
                alert(`Error: ${result.message}`);
            }
        } catch (error) {
            console.error("Error stopping training:", error);
            alert("Failed to stop training.");
        }
    };

    // Poll rendering status
    const pollRenderStatus = async () => {
        try {
            const response = await fetch("/training/render_status");
            const { rendering } = await response.json();
            updateStatus(true, rendering);
            if (!rendering) setTimeout(pollRenderStatus, 3000);
        } catch (error) {
            console.error("Error polling render status:", error);
        }
    };

    // Poll training status
    const pollTrainingStatus = async () => {
        try {
            const response = await fetch("/training/training_status");
            const { training } = await response.json();
            updateStatus(training, false);
        } catch (error) {
            console.error("Error polling training status:", error);
            updateStatus(false, false);
        }
    };

    // Initial status checks
    (async () => {
        updateStatus(false, false);
        await pollTrainingStatus();
    })();
}

// Dynamically load content and initialize
async function loadDynamicContent(url, onLoad) {
    const contentContainer = document.getElementById("dynamic-content");
    if (!contentContainer) {
        console.error("Content container not found.");
        return;
    }

    try {
        const response = await fetch(url);
        if (response.ok) {
            contentContainer.innerHTML = await response.text();

            // Execute callback after content loads
            if (typeof onLoad === "function") onLoad();

            // Call listeners conditionally based on the loaded URL
            if (url.includes("/dashboard/training") && typeof initializeListenersForTrainingDashboard === "function") {
                initializeListenersForTrainingDashboard();
            } else if (url.includes("/tensorboard")) {
                console.log("TensorBoard content loaded.");
            } else {
                console.warn("No specific listeners defined for this page.");
            }
        } else {
            contentContainer.innerHTML = "<p>Error loading content. Please try again later.</p>";
        }
    } catch (error) {
        console.error("Failed to load content:", error);
        contentContainer.innerHTML = "<p>Error loading content. Please check your connection.</p>";
    }
}


// Collect training configuration from the UI
function collectTrainingConfig() {
    const config = {
        training_config: {},
        hyperparameters: {},
        wrappers: [],
        callbacks: [],
    };

    document.querySelectorAll(".config-input").forEach((input) => {
        const name = input.name;
        const value = input.value;
        if (name.startsWith("hyperparameters")) {
            config.hyperparameters[name.split("[")[1].replace("]", "")] = value;
        } else if (name.startsWith("training_config")) {
            config.training_config[name.split("[")[1].replace("]", "")] = value;
        }
    });

    document.querySelectorAll(".wrapper-checkbox:checked").forEach((checkbox) => {
        config.wrappers.push(checkbox.value);
    });

    document.querySelectorAll(".callback-checkbox:checked").forEach((checkbox) => {
        config.callbacks.push(checkbox.value);
    });

    return config;
}

document.addEventListener("DOMContentLoaded", async () => {
    initializeHeaderControls(); // Set up header controls

    // Automatically load the Training Dashboard on initial load
    await loadDynamicContent("/dashboard/training", initializeHeaderControls);

    // Add event listener for the TensorBoard link
    const tensorboardLink = document.getElementById("tensorboard-link");
    if (tensorboardLink) {
        tensorboardLink.addEventListener("click", async (event) => {
            event.preventDefault();
            await loadDynamicContent("/tensorboard");
        });
    } else {
        console.error("TensorBoard link not found.");
    }

    // Add event listener for the Training Dashboard link
    const trainingLink = document.getElementById("training-dashboard-link");
    if (trainingLink) {
        trainingLink.addEventListener("click", async (event) => {
            event.preventDefault();
            await loadDynamicContent("/dashboard/training", initializeHeaderControls);
        });
    } else {
        console.error("Training Dashboard link not found.");
    }
});
