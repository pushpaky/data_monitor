console.log("✅ script_battery.js loaded");

document.getElementById("batteryForm").addEventListener("submit", async function (e) {
  e.preventDefault();

  const deviceId = document.getElementById("device_id").value;
  const resultDiv = document.getElementById("batteryResult");
  resultDiv.innerHTML = "Loading battery status...";

  try {
    const response = await fetch(`/api/battery-status?device_id=${encodeURIComponent(deviceId)}`);
    const data = await response.json();

    if (!response.ok) {
      resultDiv.innerHTML = `<p style="color:red;">Error: ${data.detail}</p>`;
      return;
    }

    // Create a styled battery status display
    const batteryHtml = `
      <div style="border: 2px solid #ddd; border-radius: 10px; padding: 20px; background-color: #f9f9f9; margin-top: 10px;">
        <h3 style="margin-top: 0; color: #0c305c;">Battery Information</h3>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 15px;">
          <div>
            <p><strong>Device ID:</strong> ${data.device_id}</p>
            <p><strong>Battery Status:</strong> 
              <span style="color: ${data.status_color}; font-weight: bold; font-size: 1.1em;">
                ${data.battery_status}
              </span>
            </p>
          </div>
          <div>
            <p><strong>Voltage:</strong> ${data.voltage}</p>
            <p><strong>Battery On:</strong> 
              <span style="color: ${data.power_on ? '#28a745' : '#dc3545'}; font-weight: bold;">
                ${data.power_on ? 'Yes' : 'No'}
              </span>
            </p>
          </div>
        </div>
        <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #ddd;">
          <p><strong>Last Update:</strong> ${data.last_update ? new Date(data.last_update).toLocaleString() : 'N/A'}</p>
        </div>
        
        <!-- Battery visual indicator -->
        <div style="margin-top: 20px;">
          <p><strong>Battery Level Indicator:</strong></p>
          <div style="width: 100%; height: 30px; border: 2px solid #333; border-radius: 5px; position: relative; background-color: #f0f0f0;">
            <div style="height: 100%; background-color: ${data.status_color}; border-radius: 3px; width: ${getBatteryPercentage(data.voltage)}%; transition: width 0.3s ease;"></div>
            <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-weight: bold; color: #333;">
              ${data.voltage}
            </div>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 0.8em; margin-top: 5px; color: #666;">
            <span>3.0V (Critical)</span>
            <span>3.4V (Low)</span>
            <span>3.7V+ (Good)</span>
          </div>
        </div>
      </div>
    `;

    resultDiv.innerHTML = batteryHtml;

  } catch (err) {
    resultDiv.innerHTML = `<p style="color:red;">Error: ${err.message}</p>`;
  }
});

function getBatteryPercentage(voltageStr) {
  // Extract numeric value from voltage string (e.g., "3.75V" -> 3.75)
  const voltage = parseFloat(voltageStr);
  if (isNaN(voltage) || voltage <= 0) return 0;
  
  // Convert voltage to percentage (3.0V = 0%, 4.2V = 100%)
  const minVoltage = 3.0;
  const maxVoltage = 4.2;
  const percentage = Math.max(0, Math.min(100, ((voltage - minVoltage) / (maxVoltage - minVoltage)) * 100));
  return Math.round(percentage);
}
