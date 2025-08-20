console.log("✅ script_all_status.js loaded");

document.getElementById("dupForm").addEventListener("submit", async function (e) {
  e.preventDefault();
  console.log("🔍 Button clicked. Fetching device statuses...");

  const tableBody = document.querySelector("#statusTable tbody");
  const submitButton = document.querySelector("#dupForm button[type='submit']");

  // Show loading state with timer
  const startTime = Date.now();
  submitButton.disabled = true;
  submitButton.textContent = "Loading...";
  tableBody.innerHTML = `<tr><td colspan="4" class="table-loading">⏳ Loading device statuses... This may take a few seconds.</td></tr>`;

  try {
    const res = await fetch("/api/all-device-status");

    console.log("Response status:", res.status);
    const data = await res.json();
    console.log("✅ Parsed JSON data:", data);

    // Clear loading state
    tableBody.innerHTML = "";

    if (!Array.isArray(data) || data.length === 0) {
      tableBody.innerHTML = `<tr><td colspan="6" class="table-empty">📭 No devices found in database</td></tr>`;
      document.getElementById("statusTable").style.display = "table";
      return;
    }

    // Show table and summary
    document.getElementById("statusTable").style.display = "table";
    document.getElementById("statusSummary").style.display = "block";

    // Sort devices: Active first, then Inactive
    const sortedData = data.sort((a, b) => {
      if (a.status === "Active" && b.status !== "Active") return -1;
      if (a.status !== "Active" && b.status === "Active") return 1;
      return 0;
    });

    sortedData.forEach((device, index) => {
      const row = document.createElement("tr");

      // Add alternating row colors
      if (index % 2 === 0) {
        row.style.backgroundColor = "#f8f9fa";
      }

      // Device ID cell
      const idCell = document.createElement("td");
      idCell.textContent = device.device_id;
      idCell.title = device.device_id; // Tooltip for full ID
      row.appendChild(idCell);

      // Status cell
      const statusCell = document.createElement("td");
      const statusIcon = device.status === "Active" ? "🟢" : "🟡";
      statusCell.innerHTML = `${statusIcon} ${device.status}`;
      statusCell.style.color = device.status === "Active" ? "#28a745" : "#ffc107";
      statusCell.style.fontWeight = "bold";
      row.appendChild(statusCell);

      // Last seen cell
      const lastSeenCell = document.createElement("td");
      lastSeenCell.textContent = device.latest_time || "Unknown";
      lastSeenCell.style.fontSize = "0.9em";
      row.appendChild(lastSeenCell);

      // Hours since last cell
      const hoursSinceCell = document.createElement("td");
      const hours = device.hours_since_last;
      if (hours < 1) {
        hoursSinceCell.innerHTML = `<span style="color: #28a745; font-weight: bold;">${hours}h</span>`;
      } else if (hours < 24) {
        hoursSinceCell.innerHTML = `<span style="color: #ffc107; font-weight: bold;">${hours}h</span>`;
      } else {
        const days = Math.round(hours / 24 * 10) / 10;
        hoursSinceCell.innerHTML = `<span style="color: #dc3545; font-weight: bold;">${days}d</span>`;
      }
      row.appendChild(hoursSinceCell);

      // Record count cell
      const recordCountCell = document.createElement("td");
      recordCountCell.textContent = device.record_count?.toLocaleString() || "0";
      recordCountCell.style.textAlign = "right";
      recordCountCell.style.fontFamily = "monospace";
      row.appendChild(recordCountCell);

      // Inactive duration cell
      const durationCell = document.createElement("td");
      durationCell.textContent = device.inactive_duration || "-";
      if (device.status === "Inactive" && device.inactive_duration !== "-") {
        durationCell.style.color = "#dc3545";
        durationCell.style.fontWeight = "bold";
      } else {
        durationCell.style.color = "#ccc";
      }
      row.appendChild(durationCell);

      tableBody.appendChild(row);
    });

    // Update summary info with performance timing
    const activeCount = data.filter(d => d.status === "Active").length;
    const inactiveCount = data.length - activeCount;
    const loadTime = ((Date.now() - startTime) / 1000).toFixed(2);

    document.getElementById("activeCount").textContent = activeCount;
    document.getElementById("inactiveCount").textContent = inactiveCount;
    document.getElementById("totalCount").textContent = data.length;

    // Add performance info
    const summaryDiv = document.getElementById("statusSummary");
    const existingPerf = summaryDiv.querySelector(".perf-info");
    if (existingPerf) existingPerf.remove();

    const perfInfo = document.createElement("div");
    perfInfo.className = "perf-info";
    perfInfo.style.cssText = "margin-top: 10px; font-size: 0.9em; color: #666;";
    perfInfo.innerHTML = `⚡ Loaded in ${loadTime}s`;
    summaryDiv.appendChild(perfInfo);

    console.log(`📊 Summary: ${activeCount} active, ${inactiveCount} inactive devices (loaded in ${loadTime}s)`);

  } catch (err) {
    console.error("❌ Error fetching device status:", err);
    tableBody.innerHTML = `<tr><td colspan="4" style="color: red; text-align: center;">❌ Error loading device statuses. Please try again.</td></tr>`;
  } finally {
    // Reset button state
    submitButton.disabled = false;
    submitButton.textContent = "Get Status";
  }
});

// Clear cache button functionality
document.getElementById("clearCacheBtn").addEventListener("click", async function() {
  const button = this;
  const originalText = button.textContent;

  try {
    button.disabled = true;
    button.textContent = "Clearing...";

    const response = await fetch("/api/clear-device-status-cache", {
      method: "POST"
    });

    if (response.ok) {
      button.textContent = "Cache Cleared!";
      setTimeout(() => {
        button.textContent = originalText;
        button.disabled = false;
      }, 1500);

      // Automatically trigger a fresh fetch
      setTimeout(() => {
        document.getElementById("dupForm").dispatchEvent(new Event('submit'));
      }, 500);
    } else {
      throw new Error("Failed to clear cache");
    }
  } catch (error) {
    console.error("Error clearing cache:", error);
    button.textContent = "Error!";
    setTimeout(() => {
      button.textContent = originalText;
      button.disabled = false;
    }, 1500);
  }
});
