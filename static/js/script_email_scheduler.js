console.log("✅ script_email_scheduler.js loaded");

let deviceList = [];

async function loadSchedulerStatus() {
  const statusDisplay = document.getElementById("statusDisplay");
  statusDisplay.innerHTML = "⏳ Loading...";

  try {
    const response = await fetch("/api/email-scheduler-status");
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Failed to load status");
    }

    // Store device list for test emails
    deviceList = data.device_list || [];

    // Display status
    const statusIcon = data.scheduler_running ? "🟢" : "🔴";
    const statusText = data.scheduler_running ? "Running" : "Stopped";
    const nextRun = data.next_scheduled_run ? new Date(data.next_scheduled_run).toLocaleString() : "Not scheduled";

    statusDisplay.innerHTML = `
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
        <div style="padding: 15px; background-color: white; border-radius: 8px; border: 1px solid #ddd;">
          <h4 style="margin: 0 0 10px 0; color: #0c305c;">📊 Scheduler Status</h4>
          <p><strong>Status:</strong> ${statusIcon} ${statusText}</p>
          <p><strong>Schedule Time:</strong> ${data.schedule_time} daily</p>
          <p><strong>Next Run:</strong> ${nextRun}</p>
        </div>
        <div style="padding: 15px; background-color: white; border-radius: 8px; border: 1px solid #ddd;">
          <h4 style="margin: 0 0 10px 0; color: #0c305c;">📱 Device Configuration</h4>
          <p><strong>Configured Devices:</strong> ${data.configured_devices}</p>
          <p><strong>Device List:</strong></p>
          <ul style="margin: 5px 0 0 20px; font-size: 0.9em;">
            ${data.device_list.map(device => `<li>${device}</li>`).join('')}
          </ul>
        </div>
      </div>
    `;

    // Populate device dropdown for test emails
    populateDeviceDropdown();

  } catch (error) {
    console.error("Error loading scheduler status:", error);
    statusDisplay.innerHTML = `
      <div style="color: #dc3545; padding: 15px; background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 5px;">
        <h4 style="margin-top: 0;">❌ Error Loading Status</h4>
        <p>${error.message}</p>
      </div>
    `;
  }
}

function populateDeviceDropdown() {
  const dropdown = document.getElementById("testDeviceId");
  dropdown.innerHTML = "";
  
  deviceList.forEach(device => {
    const option = document.createElement("option");
    option.value = device;
    option.textContent = device;
    dropdown.appendChild(option);
  });
}

async function sendTestEmailAll() {
  const resultDiv = document.getElementById("testEmailResult");
  resultDiv.innerHTML = "⏳ Sending test emails to all devices...";

  try {
    const response = await fetch("/api/send-test-email", {
      method: "POST"
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Failed to send test emails");
    }

    resultDiv.innerHTML = `
      <div style="color: #155724; padding: 15px; background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 5px;">
        <h4 style="margin-top: 0;">✅ Test Emails Sent Successfully</h4>
        <p>${data.message}</p>
        <p><strong>Devices Processed:</strong> ${data.devices_processed}</p>
        <p><em>Check your email inbox for the test reports.</em></p>
      </div>
    `;

  } catch (error) {
    console.error("Error sending test emails:", error);
    resultDiv.innerHTML = `
      <div style="color: #721c24; padding: 15px; background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 5px;">
        <h4 style="margin-top: 0;">❌ Failed to Send Test Emails</h4>
        <p>${error.message}</p>
      </div>
    `;
  }
}

function sendTestEmailSingle() {
  if (deviceList.length === 0) {
    alert("No devices configured. Please check your email configuration.");
    return;
  }

  document.getElementById("testEmailForm").style.display = "block";
  document.getElementById("testEmailResult").innerHTML = "";
}

async function sendTestEmailToDevice() {
  const deviceId = document.getElementById("testDeviceId").value;
  const resultDiv = document.getElementById("testEmailResult");
  
  if (!deviceId) {
    alert("Please select a device.");
    return;
  }

  resultDiv.innerHTML = `⏳ Sending test email for device: ${deviceId}...`;

  try {
    const response = await fetch(`/api/send-test-email?device_id=${encodeURIComponent(deviceId)}`, {
      method: "POST"
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Failed to send test email");
    }

    resultDiv.innerHTML = `
      <div style="color: #155724; padding: 15px; background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 5px;">
        <h4 style="margin-top: 0;">✅ Test Email Sent Successfully</h4>
        <p>${data.message}</p>
        <p><strong>Device ID:</strong> ${data.device_id}</p>
        <p><em>Check your email inbox for the test report.</em></p>
      </div>
    `;

    // Hide the form
    document.getElementById("testEmailForm").style.display = "none";

  } catch (error) {
    console.error("Error sending test email:", error);
    resultDiv.innerHTML = `
      <div style="color: #721c24; padding: 15px; background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 5px;">
        <h4 style="margin-top: 0;">❌ Failed to Send Test Email</h4>
        <p>${error.message}</p>
      </div>
    `;
  }
}

function cancelTestEmail() {
  document.getElementById("testEmailForm").style.display = "none";
  document.getElementById("testEmailResult").innerHTML = "";
}

// Load status when page loads
window.addEventListener("load", function() {
  loadSchedulerStatus();
  
  // Auto-refresh status every 30 seconds
  setInterval(loadSchedulerStatus, 30000);
});
