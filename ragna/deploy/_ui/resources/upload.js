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
  const documentUpload = await response.json();

  const parameters = documentUpload.parameters;
  var body = new FormData();
  for (const [key, value] of Object.entries(parameters.data)) {
    body.append(key, value);
  }
  body.append("file", file);

  await fetch(parameters.url, {
    method: parameters.method,
    body: body,
  });

  return documentUpload.document;
}
