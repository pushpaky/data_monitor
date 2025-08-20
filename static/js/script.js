
document.getElementById("dataForm").addEventListener("submit", async function (e) {
  e.preventDefault();

  const deviceId = document.getElementById("device_id").value;
  const startDate = document.getElementById("start_date").value;
  const endDate = document.getElementById("end_date").value;
  const resultBox = document.getElementById("result");

  try {
    resultBox.innerHTML = "<p>⏳ Fetching data...</p>";

    const res = await fetch(`/api/get-data?device_id=${deviceId}&start_date=${startDate}&end_date=${endDate}`);
    const data = await res.json();

    if (data.error) {
      resultBox.innerHTML = `<p style="color:red;">❌ ${data.error}</p>`;
      return;
    }

    // ✅ Show number of records and date range
    resultBox.innerHTML = `<p>✅ <strong>${data.count} records</strong> found from <strong>${data.start_time}</strong> to <strong>${data.end_time}</strong></p>`;

    // 🎯 Send data to chart API
    const chartRes = await fetch("/api/render-chart", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        records: data.records,
        start_date: startDate,
        end_date: endDate
      })
    });

    if (chartRes.ok) {
      const blob = await chartRes.blob();
      const imageUrl = URL.createObjectURL(blob);

      document.getElementById("chartImage").src = imageUrl;
      document.getElementById("chartImage").style.display = "block";
      document.getElementById("chart-title").style.display = "block";

      // 📥 Set PNG download link
      const chartLink = document.getElementById("download-chart");
      chartLink.href = imageUrl;

      // 📥 Generate CSV
      let csv = "devicetime,csm\n";
      data.records.forEach(rec => {
        const csm = rec?.data?.evt?.csm || 0;
        csv += `${rec.devicetime},${csm}\n`;
      });

      const csvBlob = new Blob([csv], { type: "text/csv" });
      const csvUrl = URL.createObjectURL(csvBlob);
      document.getElementById("download-csv").href = csvUrl;

      document.getElementById("download-buttons").style.display = "flex";
    } else {
      resultBox.innerHTML += "<p>⚠️ Chart rendering failed.</p>";
    }

  } catch (err) {
    console.error("Error fetching data:", err);
    resultBox.innerHTML = "<p style='color:red;'>❌ Fetch failed.</p>";
  }
});

