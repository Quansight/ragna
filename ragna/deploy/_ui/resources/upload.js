function upload(files, token, informationEndpoint, final_callback) {

  async function uploadBatches() {

    let index = 0;
    let uploaded = [];

    const batchSize = 500;
    const queue = Array.from(files);

    while(index < files.length) {
      const batch = queue.splice(0, batchSize);
      await Promise.all(
        batch.map(file => uploadFile(file, token, informationEndpoint))
      ).then(results => {
        uploaded.push(...results);
      });
      index += batch.length;
    }
    return(uploaded);
  }

  uploadBatches().then(final_callback);
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
