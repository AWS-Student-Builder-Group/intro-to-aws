// UI only. Flow: ask the Lambda for presigned URLs -> upload straight to S3 -> show the
// download link. The AWS calls live in aws.js.

import { isConfigured, requestUrls, uploadToS3 } from "./aws.js";

const $ = (id) => document.getElementById(id);
const fileInput = $("file");
const dropzone = $("dropzone");
const statusEl = $("status");

let countdownTimer = null;

function setStatus(message, kind = "") {
  statusEl.textContent = message;
  statusEl.className = kind;
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
  if (!isConfigured()) {
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
