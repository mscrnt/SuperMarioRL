// path: /static/js/metrics_dashboard.js

/**
 * Fetch and initialize metrics for the dashboard.
 */
async function fetchMetricsData() {
    try {
        const response = await fetch("/metrics/data"); // API to fetch metrics
        if (!response.ok) throw new Error("Failed to fetch metrics data.");

        const metricsData = await response.json();
        populateMetricsCharts(metricsData);
        console.log("Metrics data fetched and charts updated.");
    } catch (error) {
        console.error("Error fetching metrics data:", error);
    }
}

/**
 * Populate and update all dashboard metrics.
 * @param {Object} data Metrics data from the server
 */
function populateMetricsCharts(data) {
    const monitorRewards = Object.values(data.env0 || {}).reduce((a, b) => a + b, 0);
    const trainingRewards = Object.values(data.training || {}).reduce((a, b) => a + b, 0);

    // Update the Reward Comparison Meter
    updateRewardComparisonMeter(monitorRewards, trainingRewards);

    // Update other charts
    destroyAndUpdateChart("env0-line-chart", "Monitor Env - Line Chart", data.env0, "line");
    destroyAndUpdateChart("training-line-chart", "Training - Line Chart", data.training, "line");
    destroyAndUpdateChart("env0-reward-chart", "Monitor Env - Reward Distribution", data.rewardDistribution, "pie");
    destroyAndUpdateChart("training-reward-chart", "Training - Reward Distribution", data.rewardDistribution, "pie");

    // Update placeholders
    destroyAndUpdateChart("env0-placeholder-chart", "Monitor Env - Placeholder", { Placeholder: 1 }, "bar");
    destroyAndUpdateChart("training-placeholder-chart", "Training - Placeholder", { Placeholder: 1 }, "bar");
}

/**
 * Refresh metrics every 10 seconds.
 */
function startMetricsRefresh() {
    fetchMetricsData(); // Fetch immediately on page load
    setInterval(fetchMetricsData, 10000); // Refresh every 10 seconds
}

/**
 * Destroy an existing chart and recreate it with new data.
 * @param {string} chartId ID of the canvas element for the chart
 * @param {string} label Label for the chart
 * @param {Object} data Data for the chart
 * @param {string} type Chart type (e.g., "line", "pie", "bar")
 */
function destroyAndUpdateChart(chartId, label, data, type) {
    const ctx = document.getElementById(chartId).getContext("2d");

    // Ensure the chart instance is destroyed before creating a new one
    if (window.charts && window.charts[chartId]) {
        window.charts[chartId].destroy();
    } else {
        if (!window.charts) window.charts = {};
    }

    const labels = Object.keys(data).map((key) => (type === "line" ? `Step ${key}` : key));
    const values = Object.values(data);

    window.charts[chartId] = new Chart(ctx, {
        type,
        data: {
            labels,
            datasets: [
                {
                    label,
                    data: values,
                    borderColor: type === "line" ? "blue" : undefined,
                    borderWidth: type === "line" ? 2 : undefined,
                    backgroundColor: type === "pie" ? ["gold", "silver", "gray"] : undefined,
                },
            ],
        },
    });
}

/**
 * Update the reward comparison meter.
 * @param {number} monitorReward Total rewards for Monitor Env
 * @param {number} trainingReward Total rewards for Training Envs
 */
function updateRewardComparisonMeter(monitorReward, trainingReward) {
    const totalReward = monitorReward + trainingReward;
    const monitorPercentage = (monitorReward / totalReward) * 100;

    const tick = document.getElementById("reward-meter-tick");
    if (tick) {
        tick.style.left = `${monitorPercentage}%`;
        console.log(`Meter Updated: Monitor (${monitorReward}) vs Training (${trainingReward})`);
    }
}

/**
 * Initialize video feed logic with placeholder.
 */
function initializeVideoFeed() {
    const videoPlaceholder = document.getElementById("video-placeholder");
    const videoFeed = document.getElementById("video-feed");

    if (!videoPlaceholder || !videoFeed) {
        console.error("Video elements are missing in the DOM.");
        return;
    }

    // Ensure placeholder is visible by default
    videoPlaceholder.style.display = "block";
    videoFeed.style.display = "none";

    const checkRenderStatus = async () => {
        try {
            const response = await fetch("/training/render_status");
            const { rendering } = await response.json();

            if (rendering) {
                videoPlaceholder.style.display = "none";
                videoFeed.style.display = "block";
            } else {
                setTimeout(checkRenderStatus, 1000); // Retry every second
            }
        } catch (error) {
            console.error("Error checking render status:", error);
            setTimeout(checkRenderStatus, 1000); // Retry in case of error
        }
    };

    checkRenderStatus();
}

/**
 * Initialize listeners for Metrics Dashboard.
 */
function initializeListenersForMetricsDashboard() {
    initializeVideoFeed();
    startMetricsRefresh(); // Start the periodic refresh
    console.log("Listeners for Metrics Dashboard initialized.");
}

// Event listener for when the Metrics Dashboard is loaded dynamically
document.addEventListener("DOMContentLoaded", () => {
    if (window.location.pathname.includes("/dashboard/metrics")) {
        initializeListenersForMetricsDashboard();
    }
});
