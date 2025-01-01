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

        // Use placeholder values if fetching metrics data fails
        populateMetricsCharts({}); // Pass an empty object
    }
}

/**
 * Populate and update all dashboard metrics.
 * @param {Object} data Metrics data from the server
 */
function populateMetricsCharts(data) {
    // Calculate Kill/Death Ratios
    const monitorKills = data.env0Stats?.enemy_kills || 0;
    const monitorDeaths = data.env0Stats?.deaths || 1; // Avoid division by zero
    const monitorKD = (monitorKills / monitorDeaths).toFixed(2) || "6.9";

    const trainingKills = data.trainingStats?.enemy_kills || 0;
    const trainingDeaths = data.trainingStats?.deaths || 1; // Avoid division by zero
    const trainingKD = (trainingKills / trainingDeaths).toFixed(2) || "6.9";

    // Display K/D Ratios
    updateKDDisplay("env0-kd-display", "Monitor K/D", monitorKD);
    updateKDDisplay("training-kd-display", "Training K/D", trainingKD);

    // Update the Reward Comparison Meter
    const monitorRewards = Object.values(data.env0 || {}).reduce((a, b) => a + b, 0);
    const trainingRewards = Object.values(data.training || {}).reduce((a, b) => a + b, 0);
    updateRewardComparisonMeter(monitorRewards, trainingRewards);

    // Update other charts
    destroyAndUpdateChart("env0-reward-chart", "Monitor Env - Reward Distribution", data.rewardDistribution || {}, "pie");
    destroyAndUpdateChart("training-reward-chart", "Training - Reward Distribution", data.rewardDistribution || {}, "pie");
}

/**
 * Refresh metrics every 10 seconds.
 */
function startMetricsRefresh() {
    fetchMetricsData(); // Fetch immediately on page load
    setInterval(fetchMetricsData, 10000); // Refresh every 10 seconds
}

/**
 * Display K/D Ratio as a float.
 * @param {string} elementId ID of the element where the K/D should be displayed
 * @param {string} label Label for the display
 * @param {string} kdRatio The calculated K/D ratio
 */
function updateKDDisplay(elementId, label, kdRatio) {
    const container = document.getElementById(elementId);
    if (container) {
        container.innerHTML = `<h2>${label}</h2><p>${kdRatio}</p>`;
        console.log(`Updated ${label} to ${kdRatio}`);
    }
}

/**
 * Destroy an existing chart and recreate it with new data.
 * @param {string} chartId ID of the canvas element for the chart
 * @param {string} label Label for the chart
 * @param {Object} data Data for the chart
 * @param {string} type Chart type (e.g., "line", "pie", "bar")
 */
function destroyAndUpdateChart(chartId, label, data, type) {
    const ctx = document.getElementById(chartId)?.getContext("2d");
    if (!ctx) return;

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
    const monitorPercentage = totalReward > 0 ? (monitorReward / totalReward) * 100 : 50; // Default to 50%

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
                setTimeout(checkRenderStatus, 1000);
            }
        } catch (error) {
            console.error("Error checking render status:", error);
            setTimeout(checkRenderStatus, 1000);
        }
    };

    checkRenderStatus();
}

/**
 * Initialize listeners for Metrics Dashboard.
 */
function initializeListenersForMetricsDashboard() {
    initializeVideoFeed();
    startMetricsRefresh();
    console.log("Listeners for Metrics Dashboard initialized.");
}

// Event listener for when the Metrics Dashboard is loaded dynamically
document.addEventListener("DOMContentLoaded", () => {
    if (window.location.pathname.includes("/dashboard/metrics")) {
        initializeListenersForMetricsDashboard();
    }
});
