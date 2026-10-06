const contentTypeOf = (file) => file.type || "application/octet-stream";

export function isConfigured() {
  return !window.APP_CONFIG.FUNCTION_URL.includes("REPLACE-ME");
}

// Step 1: ask the Lambda for presigned upload and download URLs.
export async function requestUrls(file) {
  const res = await fetch(window.APP_CONFIG.FUNCTION_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      filename: file.name,
      size: file.size,
      contentType: contentTypeOf(file),
    }),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.error || `Lambda returned ${res.status}`);
  return body;
}

// Step 2: send the file straight to S3 using the presigned URL.
// onProgress receives a number from 0 to 1.
export function uploadToS3(file, { uploadUrl, fields }, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open(fields ? "POST" : "PUT", uploadUrl);

    let payload = file;
    if (fields) {
      payload = new FormData();
      Object.entries(fields).forEach(([k, v]) => payload.append(k, v));
      payload.append("file", file); // must be the last field
    } else {
      xhr.setRequestHeader("Content-Type", contentTypeOf(file));
    }

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress(e.loaded / e.total);
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) return resolve();
      // S3 explains refusals in an XML body, e.g. <Code>AccessDenied</Code><Message>...</Message>
      const code = /<Code>(.*?)<\/Code>/.exec(xhr.responseText)?.[1];
      const message = /<Message>(.*?)<\/Message>/.exec(xhr.responseText)?.[1];
      reject(new Error(`S3 rejected the upload (${xhr.status}${code ? ` ${code}` : ""}). ${message || ""}`));
    };
    xhr.onerror = () => reject(new Error("Upload failed. Check bucket CORS and your network."));
    xhr.send(payload);
  });
}
