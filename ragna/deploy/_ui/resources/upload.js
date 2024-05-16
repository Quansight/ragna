function upload(files, informationEndpoint, final_callback) {
  uploadBatches(files, informationEndpoint).then(final_callback);
}

async function uploadBatches(files, informationEndpoint) {
  const batchSize = 500;
  const queue = Array.from(files);

  let uploaded = [];

  while (queue.length) {
    const batch = queue.splice(0, batchSize);
    await Promise.all(batch.map((file) => uploadFile(file, informationEndpoint))).then(
      (results) => {
        uploaded.push(...results);
      },
    );
  }

  return uploaded;
}

async function uploadFile(file, informationEndpoint) {
  const response = await fetch(informationEndpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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
