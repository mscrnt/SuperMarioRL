// path: app/static/js/index.js

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

async function loadDynamicContent(url, onLoad, resetToDefault = false) {
    const contentContainer = document.getElementById("dynamic-content");
    if (!contentContainer) {
        console.error("Content container not found.");
        return;
    }

    try {
        const response = await fetch(url);
        if (response.ok) {
            contentContainer.innerHTML = await response.text();

            // Reset configuration to default if specified
            if (resetToDefault) {
                await resetToDefaultConfig();
            } else {
                await loadCurrentConfig(); // Always load the active config
            }

            // Execute callback after content loads
            if (typeof onLoad === "function") onLoad();

            // Highlight the active link dynamically
            const navLinks = document.querySelectorAll(".nav-link");
            navLinks.forEach(link => {
                link.classList.remove("active");
                if (link.getAttribute("href") === url) {
                    link.classList.add("active");
                }
            });

            // Call listeners conditionally based on the loaded URL
            if (url.includes("/dashboard/training") && typeof initializeListenersForTrainingDashboard === "function") {
                initializeListenersForTrainingDashboard();
            }

            console.log(`Content loaded for URL: ${url}`);
        } else {
            contentContainer.innerHTML = "<p>Error loading content. Please try again later.</p>";
        }
    } catch (error) {
        console.error("Failed to load content:", error);
        contentContainer.innerHTML = "<p>Error loading content. Please check your connection.</p>";
    }
}


async function resetToDefaultConfig() {
    try {
        const response = await fetch("/training/reset_to_default", { method: "POST" });
        const result = await response.json();
        if (response.ok) {
            console.log(result.message || "Configuration reset to default.");
        } else {
            console.error("Error resetting configuration:", result.message);
        }
    } catch (error) {
        console.error("Error resetting to default configuration:", error);
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

    // Collect training and hyperparameters input values
    document.querySelectorAll(".config-input").forEach((input) => {
        const name = input.name;
        const value = input.value;
        if (name.startsWith("hyperparameters")) {
            config.hyperparameters[name.split("[")[1].replace("]", "")] = value;
        } else if (name.startsWith("training_config")) {
            config.training_config[name.split("[")[1].replace("]", "")] = value;
        }
    });

    // Collect wrappers
    document.querySelectorAll(".wrapper-checkbox").forEach((checkbox) => {
        if (checkbox.checked) {
            config.wrappers.push(checkbox.value); // Push the value, not dataset.key
        }
    });

    // Collect callbacks
    document.querySelectorAll(".callback-checkbox").forEach((checkbox) => {
        if (checkbox.checked) {
            config.callbacks.push(checkbox.value); // Push the value, not dataset.key
        }
    });

    console.log("Collected Configuration:", config);

    return config;
}


document.addEventListener("DOMContentLoaded", async () => {
    initializeHeaderControls(); // Set up header controls
    loadCurrentConfig();
    highlightActivePage();


    // Automatically load the Training Dashboard on initial load
    await loadDynamicContent("/dashboard/training", initializeHeaderControls, false);

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
            await loadDynamicContent("/dashboard/training", initializeHeaderControls, false);
        });
    } else {
        console.error("Training Dashboard link not found.");
    }
});

// Add event listener for the Metrics Dashboard link
const metricsLink = document.getElementById("metrics-dashboard-link");
if (metricsLink) {
    metricsLink.addEventListener("click", async (event) => {
        event.preventDefault();
        await loadDynamicContent("/dashboard/metrics", initializeListenersForMetricsDashboard);
    });
} else {
    console.error("Metrics Dashboard link not found.");
}

async function loadCurrentConfig() {
    try {
        const response = await fetch("/training/current_config");
        const { config } = await response.json();

        if (!config) {
            console.warn("No active configuration found.");
            return;
        }

        // Populate training config fields
        Object.entries(config.training_config || {}).forEach(([key, value]) => {
            const input = document.querySelector(`[name="training_config[${key}]"]`);
            if (input) {
                if (input.tagName === "SELECT") {
                    input.value = value !== undefined && value !== null ? value.toString() : "False";
                } else {
                    input.value = value !== undefined && value !== null ? value : "";
                }
            }
        });

        // Populate hyperparameters fields
        Object.entries(config.hyperparameters || {}).forEach(([key, value]) => {
            const input = document.querySelector(`[name="hyperparameters[${key}]"]`);
            if (input) {
                input.value = value !== undefined && value !== null ? value : "";
            }
        });

        // Set default for normalize_advantage if missing
        const normalizeAdvantage = document.querySelector(`[name="hyperparameters[normalize_advantage]"]`);
        if (normalizeAdvantage && !normalizeAdvantage.value) {
            normalizeAdvantage.value = "True";
        }

        // Set wrapper and callback checkboxes
        document.querySelectorAll(".wrapper-checkbox").forEach((checkbox) => {
            checkbox.checked = config.enabled_wrappers.includes(checkbox.value) || checkbox.hasAttribute("disabled");
        });

        document.querySelectorAll(".callback-checkbox").forEach((checkbox) => {
            checkbox.checked = config.enabled_callbacks.includes(checkbox.value) || checkbox.hasAttribute("disabled");
        });

        // Ensure random_stages defaults to DEFAULT_TRAINING_CONFIG value
        const randomStagesSelect = document.querySelector(`[name="training_config[random_stages]"]`);
        if (randomStagesSelect && !randomStagesSelect.value) {
            randomStagesSelect.value = config.random_stages ? "True" : "False";
        }

        console.log("Active configuration loaded successfully.");
    } catch (error) {
        console.error("Error loading current configuration:", error);
    }
}


function highlightActivePage() {
    // Get the current URL path
    const currentPath = window.location.pathname;

    // Find all navigation links
    const navLinks = document.querySelectorAll(".nav-link");

    // Remove the active class from all links and set the active class for the matching path
    navLinks.forEach(link => {
        link.classList.remove("active");
        if (link.getAttribute("href") === currentPath) {
            link.classList.add("active");
        }
    });

    console.log(`Active page highlighted: ${currentPath}`);
}
