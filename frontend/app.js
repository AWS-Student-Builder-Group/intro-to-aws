// Flow: ask the Lambda for presigned URLs -> upload straight to S3 -> show the download link.
//
// Lambda contract
//   request : POST {filename, size, contentType}
//   response: {uploadUrl, downloadUrl, expiresIn, fields?}
//   If `fields` is present, uploadUrl is a presigned POST (multipart form, file last).
//   Otherwise uploadUrl is a presigned PUT.

const $ = (id) => document.getElementById(id);
const fileInput = $("file");
const dropzone = $("dropzone");
const statusEl = $("status");

let countdownTimer = null;

function setStatus(message, kind = "") {
  statusEl.textContent = message;
  statusEl.className = kind;
}

async function requestUrls(file) {
  const res = await fetch(window.APP_CONFIG.FUNCTION_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      filename: file.name,
      size: file.size,
      contentType: file.type || "application/octet-stream",
    }),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.error || `Lambda returned ${res.status}`);
  return body;
}

function uploadToS3(file, { uploadUrl, fields }, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open(fields ? "POST" : "PUT", uploadUrl);

    let payload = file;
    if (fields) {
      payload = new FormData();
      Object.entries(fields).forEach(([k, v]) => payload.append(k, v));
      payload.append("file", file); // must be the last field
    } else {
      xhr.setRequestHeader("Content-Type", file.type || "application/octet-stream");
    }

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress(e.loaded / e.total);
    };
    xhr.onload = () =>
      xhr.status >= 200 && xhr.status < 300
        ? resolve()
        : reject(new Error(`S3 rejected the upload (${xhr.status}). Check bucket CORS.`));
    xhr.onerror = () => reject(new Error("Upload failed. Check bucket CORS and your network."));
    xhr.send(payload);
  });
}

function showResult(downloadUrl, expiresIn) {
  $("link").value = downloadUrl;
  $("result").hidden = false;

  clearInterval(countdownTimer);
  const expiresAt = Date.now() + expiresIn * 1000;
  const tick = () => {
    const left = Math.max(0, Math.round((expiresAt - Date.now()) / 1000));
    $("expiry").textContent =
      left > 0
        ? `Expires in ${Math.floor(left / 60)}m ${String(left % 60).padStart(2, "0")}s`
        : "This link has expired.";
    if (left === 0) clearInterval(countdownTimer);
  };
  tick();
  countdownTimer = setInterval(tick, 1000);
}

async function handleFile(file) {
  if (!file) return;
  if (window.APP_CONFIG.FUNCTION_URL.includes("REPLACE-ME")) {
    setStatus("Set FUNCTION_URL in frontend/config.js first.", "error");
    return;
  }

  $("result").hidden = true;
  $("progress").hidden = false;
  $("bar").style.width = "0";
  $("dropzone-text").textContent = file.name;

  try {
    setStatus("Requesting upload link...");
    const urls = await requestUrls(file);

    setStatus("Uploading...");
    await uploadToS3(file, urls, (p) => {
      $("bar").style.width = `${Math.round(p * 100)}%`;
    });

    setStatus("Done! Share the link below.", "ok");
    showResult(urls.downloadUrl, urls.expiresIn);
  } catch (err) {
    setStatus(err.message, "error");
  } finally {
    fileInput.value = "";
  }
}

fileInput.addEventListener("change", () => handleFile(fileInput.files[0]));

["dragenter", "dragover"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.add("over");
  })
);
["dragleave", "drop"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.remove("over");
  })
);
dropzone.addEventListener("drop", (e) => handleFile(e.dataTransfer.files[0]));

$("copy").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText($("link").value);
    $("copy").textContent = "Copied!";
  } catch {
    $("link").select();
    $("copy").textContent = "Press Ctrl/Cmd+C";
  }
  setTimeout(() => ($("copy").textContent = "Copy"), 1500);
});
