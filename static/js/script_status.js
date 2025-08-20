console.log("✅ script_status.js loaded");

document.getElementById("dupForm").addEventListener("submit", async function (e) {
  e.preventDefault();

  const deviceId = document.getElementById("device_id").value.trim();
  const resultDiv = document.getElementById("result");

  if (!deviceId) {
    resultDiv.innerHTML = `<p style="color:red;">Please enter a device ID</p>`;
    return;
  }

  resultDiv.innerHTML = "⏳ Checking device status...";
  console.log(`Checking status for device: ${deviceId}`);

  try {
    const url = `/api/device-status?device_id=${encodeURIComponent(deviceId)}`;
    console.log(`Making request to: ${url}`);

    const response = await fetch(url);
    const data = await response.json();

    console.log(`Response status: ${response.status}`);
    console.log(`Response data:`, data);

    if (!response.ok) {
      if (response.status === 404) {
        resultDiv.innerHTML = `
          <div style="color: #dc3545; padding: 15px; background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 5px;">
            <h4 style="margin-top: 0;">❌ Device Not Found</h4>
            <p><strong>Device ID:</strong> ${deviceId}</p>
            <p>This device was not found in the database. Please check:</p>
            <ul>
              <li>The device ID is correct</li>
              <li>The device has sent data to the system</li>
              <li>Try checking the "All Device Status" page for available devices</li>
            </ul>
          </div>
        `;
      } else {
        resultDiv.innerHTML = `<p style="color:red;">Error ${response.status}: ${data.detail || 'Unknown error'}</p>`;
      }
      return;
    }

    // Success - display device status
    const statusColor = data.status === 'active' ? '#28a745' : '#ffc107';
    const statusIcon = data.status === 'active' ? '🟢' : '🟡';

    resultDiv.innerHTML = `
      <div style="padding: 15px; background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 5px;">
        <h4 style="margin-top: 0; color: #155724;">✅ Device Status Found</h4>
        <p><strong>Device ID:</strong> ${data.device_id}</p>
        <p><strong>Status:</strong> ${statusIcon} <span style="color:${statusColor}; font-weight: bold;">${data.status.toUpperCase()}</span></p>
        <p><strong>Last Seen:</strong> ${new Date(data.last_seen).toLocaleString()}</p>
        ${data.inactive_since ? `<p><strong>Inactive Since:</strong> ${new Date(data.inactive_since).toLocaleString()}</p>` : ""}
      </div>
    `;
  } catch (err) {
    console.error('Error checking device status:', err);
    resultDiv.innerHTML = `
      <div style="color: #dc3545; padding: 15px; background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 5px;">
        <h4 style="margin-top: 0;">❌ Connection Error</h4>
        <p>Failed to connect to the server: ${err.message}</p>
        <p>Please check your internet connection and try again.</p>
      </div>
    `;
  }
});
