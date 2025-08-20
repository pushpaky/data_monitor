console.log("✅ script_data_table.js loaded");

let currentData = [];
let currentPage = 1;
let pageSize = 100;
let totalRecords = 0;

document.getElementById("dataForm").addEventListener("submit", async function (e) {
  e.preventDefault();

  const deviceId = document.getElementById("device_id").value.trim();
  const startDate = document.getElementById("start_date").value.trim();
  const endDate = document.getElementById("end_date").value.trim();
  pageSize = parseInt(document.getElementById("page_size").value);

  const resultDiv = document.getElementById("result");
  const tableContainer = document.getElementById("tableContainer");

  // ✅ Validate date format (YYYY-MM-DD HH:mm)
  const dateRegex = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/;
  if (!dateRegex.test(startDate) || !dateRegex.test(endDate)) {
    resultDiv.innerHTML = `<p style="color:red;">⚠ Please enter date as YYYY-MM-DD HH:mm</p>`;
    return;
  }

  // ✅ Convert to backend format (YYYY-MM-DD HH:mm:ss)
  const startFormatted = startDate + ":00";
  const endFormatted = endDate + ":00";

 

  resultDiv.innerHTML = "⏳ Loading data...";
  tableContainer.style.display = "none";

  try {
    const response = await fetch(
      `/api/get-data?device_id=${deviceId}&start_date=${encodeURIComponent(startFormatted)}&end_date=${encodeURIComponent(endFormatted)}`
    );

    const data = await response.json();

    if (data.error) {
      resultDiv.innerHTML = `<p style="color:red;">❌ ${data.error}</p>`;
      return;
    }

    if (!data.records || data.records.length === 0) {
      resultDiv.innerHTML = `<p style="color:orange;">⚠ No records found for the specified criteria.</p>`;
      return;
    }

    currentData = data.records;
    totalRecords = data.count;
    currentPage = 1;

    resultDiv.innerHTML = `<p style="color:green;">✅ Successfully loaded ${totalRecords} records</p>`;

    displayTable();
    tableContainer.style.display = "block";
  } catch (err) {
    resultDiv.innerHTML = `<p style="color:red;">❌ Error: ${err.message}</p>`;
  }
});

function displayTable() {
  const tableBody = document.getElementById("tableBody");
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = Math.min(startIndex + pageSize, currentData.length);
  const pageData = currentData.slice(startIndex, endIndex);

  // Clear existing rows
  tableBody.innerHTML = "";

  // Add rows
  pageData.forEach(record => {
    console.log("🔎 Full Record:", record);  // log entire object
    console.log("➡ binfo:", record.data?.binfo); // log binfo specifically

    const row = document.createElement("tr");

    const deviceId = record.deviceid || "N/A";
    const deviceTime = record.devicetime ? new Date(record.devicetime).toLocaleString() : "N/A";
    const etm = record.data?.evt?.etm || "N/A";
    const csm = record.data?.evt?.csm || "N/A";

    // check if binfo exists
    let bvt = "N/A";
    let bpon = "N/A";

    if (record.data?.binfo) {
        bvt = record.data.binfo.bvt !== undefined ? record.data.binfo.bvt : "N/A";
        if (record.data.binfo.bpon !== undefined) {
            bpon = record.data.binfo.bpon ? "On" : "Off";
        }
    }

    row.innerHTML = `
      <td>${deviceId}</td>
      <td>${deviceTime}</td>
      <td>${etm}</td>
      <td>${csm}</td>
      <td>${bvt !== "N/A" ? bvt + "V" : "N/A"}</td>
      <td>${bpon}</td>
    `;

    tableBody.appendChild(row);
});


  document.getElementById("totalRecords").textContent = totalRecords;
  document.getElementById("showingRecords").textContent = `${startIndex + 1}-${endIndex}`;
  document.getElementById("currentPage").textContent = currentPage;
  document.getElementById("totalPages").textContent = Math.ceil(currentData.length / pageSize);

  updatePagination();
}

function updatePagination() {
  const pagination = document.getElementById("pagination");
  const totalPages = Math.ceil(currentData.length / pageSize);

  pagination.innerHTML = "";

  const prevBtn = document.createElement("button");
  prevBtn.textContent = "« Previous";
  prevBtn.disabled = currentPage === 1;
  prevBtn.onclick = () => {
    if (currentPage > 1) {
      currentPage--;
      displayTable();
    }
  };
  pagination.appendChild(prevBtn);

  const startPage = Math.max(1, currentPage - 2);
  const endPage = Math.min(totalPages, currentPage + 2);

  if (startPage > 1) {
    const firstBtn = document.createElement("button");
    firstBtn.textContent = "1";
    firstBtn.onclick = () => {
      currentPage = 1;
      displayTable();
    };
    pagination.appendChild(firstBtn);

    if (startPage > 2) {
      const ellipsis = document.createElement("span");
      ellipsis.textContent = "...";
      ellipsis.style.margin = "0 10px";
      pagination.appendChild(ellipsis);
    }
  }

  for (let i = startPage; i <= endPage; i++) {
    const pageBtn = document.createElement("button");
    pageBtn.textContent = i;
    pageBtn.className = i === currentPage ? "active" : "";
    pageBtn.onclick = () => {
      currentPage = i;
      displayTable();
    };
    pagination.appendChild(pageBtn);
  }

  if (endPage < totalPages) {
    if (endPage < totalPages - 1) {
      const ellipsis = document.createElement("span");
      ellipsis.textContent = "...";
      ellipsis.style.margin = "0 10px";
      pagination.appendChild(ellipsis);
    }

    const lastBtn = document.createElement("button");
    lastBtn.textContent = totalPages;
    lastBtn.onclick = () => {
      currentPage = totalPages;
      displayTable();
    };
    pagination.appendChild(lastBtn);
  }

  const nextBtn = document.createElement("button");
  nextBtn.textContent = "Next »";
  nextBtn.disabled = currentPage === totalPages;
  nextBtn.onclick = () => {
    if (currentPage < totalPages) {
      currentPage++;
      displayTable();
    }
  };
  pagination.appendChild(nextBtn);
}

function exportToCSV() {
  if (currentData.length === 0) {
    alert("No data to export");
    return;
  }

  let csv = "Device ID,Device Time,ETM,CSM,Battery Voltage,Battery Power\n";

  currentData.forEach(record => {
    const deviceId = record.deviceid || "";
    const deviceTime = record.devicetime || "";
    const etm = record.data?.evt?.etm || "";
    const csm = record.data?.evt?.csm || "";
    const bvt = record.data?.binfo?.bvt || "";
    const bpon = record.data?.binfo?.bpon !== undefined ? (record.data.binfo.bpon ? "On" : "Off") : "";

    csv += `"${deviceId}","${deviceTime}","${etm}","${csm}","${bvt}","${bpon}"\n`;
  });

  const blob = new Blob([csv], { type: "text/csv" });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `aquesa_data_${new Date().toISOString().split('T')[0]}.csv`;
  a.click();
  window.URL.revokeObjectURL(url);
}

function exportToJSON() {
  if (currentData.length === 0) {
    alert("No data to export");
    return;
  }

  const jsonData = JSON.stringify(currentData, null, 2);
  const blob = new Blob([jsonData], { type: "application/json" });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `aquesa_data_${new Date().toISOString().split('T')[0]}.json`;
  a.click();
  window.URL.revokeObjectURL(url);
}

// ✅ Set default dates (last 24 hours) for text input format
window.addEventListener("load", function () {
  const now = new Date();
  const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);

  function formatDate(d) {
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, "0");
    const dd = String(d.getDate()).padStart(2, "0");
    const hh = String(d.getHours()).padStart(2, "0");
    const mi = String(d.getMinutes()).padStart(2, "0");
    return `${yyyy}-${mm}-${dd} ${hh}:${mi}`;
  }

  document.getElementById("end_date").value = formatDate(now);
  document.getElementById("start_date").value = formatDate(yesterday);
});
