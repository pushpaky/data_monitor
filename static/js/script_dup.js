function getParam(name) {
    const url = new URL(window.location.href);
    return url.searchParams.get(name);
  }
  
  async function fetchDuplicates(device_id, start, end) {
    const result = document.getElementById("result");
    result.innerHTML = "<p>⏳ Loading...</p>";
  
    try {
      const res = await fetch(`/api/find-duplicates?device_id=${encodeURIComponent(device_id)}&start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`);
      const data = await res.json();
  
      console.log("Data received:", data);  // Debug
  
      if (data.error) {
        result.innerHTML = `<p style="color:red;">❌ ${data.error}</p>`;
        return;
      }
  
      if (!data.duplicates || data.duplicates.length === 0) {
        result.innerHTML = "<p>✅ No duplicates found.</p>";
        return;
      }
  
      let html = `<p><strong>${data.count} duplicate record(s) found:</strong></p>`;
      html += "<table border='1' cellpadding='8'><tr><th>Device ID</th><th>Device Time</th></tr>";
  
      data.duplicates.forEach(d => {
        html += `<tr><td>${d.deviceid}</td><td>${d.devicetime}</td></tr>`;
      });
  
      html += "</table>";
      result.innerHTML = html;
  
    } catch (err) {
      console.error("Fetch error:", err);
      result.innerHTML = "<p style='color:red;'>Error fetching duplicates.</p>";
    }
  }
  
  document.addEventListener("DOMContentLoaded", () => {
    const device_id = getParam("device_id");
    const start = getParam("start");
    const end = getParam("end");
  
    if (device_id && start && end) {
      fetchDuplicates(device_id, start, end);
    }
  
    // Also handle manual form submission
    document.getElementById("dupForm").addEventListener("submit", async function (e) {
      e.preventDefault();
      const device_id = document.getElementById("device_id").value.trim();
      const start = document.getElementById("start").value.trim();
      const end = document.getElementById("end").value.trim();
      fetchDuplicates(device_id, start, end);
    });
  });
    