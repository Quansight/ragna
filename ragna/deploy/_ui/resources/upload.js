function upload(files, token, informationsEndpoint, final_callback) {
  Promise.all(
    Array.from(files).map((file) => {
      return uploadFile(file, token, informationsEndpoint);
    }),
  ).then(final_callback);
}

async function uploadFile(file, token, informationEndpoint) {
  const response = await fetch(informationEndpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ name: file.name }),
  });
  const documentInfo = await response.json();

  var body = new FormData();
  for (const [key, value] of Object.entries(documentInfo.data)) {
    body.append(key, value);
  }
  body.append("file", file);

  await fetch(documentInfo.url, {
    method: "POST",
    body: body,
  });

  return documentInfo.document;
}
