function getParam(name) {
  const url = new URL(window.location.href);
  return url.searchParams.get(name);
}

  async function fetchMissing(device_id, start, end) {
    const result = document.getElementById("result");
    result.innerHTML = "⏳ Checking…";
  
    try {
      const res = await fetch(`/api/missing-intervals?device_id=${encodeURIComponent(device_id)}&start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`);
      const data = await res.json();
      // console.log("API ➜", data);
    
      if (data.message === "No records found") {
        result.innerHTML = `<p style="color:red;">❌ ${data.message}</p>`;
        return;
      }
    
      if (!data.missing_intervals.length) {
        result.innerHTML = `<p style="color:green;">✅ No missing intervals found.</p>`;
        return;
      }
    
      let html = `<p><strong>⚠️ ${data.count} missing intervals:</strong></p>`;
      html += "<table border='1'><tr><th>Start</th><th>End</th></tr>";
      data.missing_intervals.forEach(i => {
        html += `<tr><td>${i.missing_interval_start}</td><td>${i.missing_interval_end}</td></tr>`;
      });
      html += "</table>";
      result.innerHTML = html;
    
    } catch (err) {
      console.error(err);
      result.innerHTML = `<p style="color:red;">❌ ${err.message || err}</p>`;
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
      fetchMissing(device_id, start, end);
    });
  });