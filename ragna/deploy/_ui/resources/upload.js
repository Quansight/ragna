function upload(files, token, informationsEndpoint, final_callback) {
  const batchSize = 500; // Maximum number of concurrent uploads
  let currentIndex = 0; // Tracks the index of the current file to be uploaded
  let successfullyUploaded = []; // Array to hold the results

  // Function to upload a single batch of files
  function uploadBatch() {
    // Get the next batch of files based on the current index and batch size
    const batch = Array.from(files).slice(currentIndex, currentIndex + batchSize);
    currentIndex += batchSize;
    // Map over the batch to create an array of upload promises
    return Promise.all(
      batch.map(file => uploadFile(file, token, informationsEndpoint))
    ).then(results => {
      // Concatenate the results of the current batch to the main array
      successfullyUploaded = successfullyUploaded.concat(results);
      // If there are more files to upload, recursively call uploadBatch again
      if (currentIndex < files.length) {
        return uploadBatch();
      } else {
        // If all files are uploaded, invoke the final callback with the results
        final_callback(successfullyUploaded);
      }
    });
  }

  // Start uploading the first batch
  uploadBatch().catch(error => {
    console.error("An error occurred during the upload process", error);
    // You might want to call your final callback with an error or partial results
    final_callback(successfullyUploaded);
  });
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
