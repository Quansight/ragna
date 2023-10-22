

function upload(files, token, informationsEndpoint, final_callback) {
    var uploaded_documents = [] 

    Array.from(files).map(file => {

        getUploadInformations(file, token, informationsEndpoint).then(

                function(uploadInformations) {
                        uploadFile(uploadInformations.url, uploadInformations.data, file)
                        uploaded_documents.push(uploadInformations.document)
                        if (uploaded_documents.length == files.length) {
                            final_callback(uploaded_documents);
                        }
                }
        );
        
    })
    
    
}

async function getUploadInformations(file, token, informationsEndpoint) {
        const response = await fetch(
            `${informationsEndpoint}?name=${file.name}`,
            {"headers": {"Authorization": `Bearer ${token}`}},
        );
        const uploadInformations = await response.json();

        return uploadInformations
}

async function uploadFile(url, data, file) {
    var body = new FormData()

    for (const [key, value] of Object.entries(data)) {
      body.append(key, value);
    }
    body.append('file', file );

    const payload = {
        method: 'POST',
        body: body
    }

    const response = fetch(url, payload).then((response) => response.json())
    
    return response
    
}
