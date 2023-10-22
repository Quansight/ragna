

function upload(files, user, informationsEndpoint, uploadEndpoint, final_callback) {
    
    var uploaded_documents = [] 

    Array.from(files).map(file => {

        getUploadInformations(file, user, informationsEndpoint).then(

                function(uploadInformations) { 
                        
                        uploadFile(file, uploadInformations, uploadEndpoint).then(
                                function(response){
                                        
                                        uploaded_documents.push(response)
                                        if (uploaded_documents.length == files.length) {
                                            final_callback(uploaded_documents);
                                        }
                                    
                                }
                        )
                }
        );
        
    })
    
    
}
 
async function getUploadInformations(file, user, informationsEndpoint) {
        const response = await fetch(informationsEndpoint+"?name="+file.name+"&user="+user );
        const uploadInformations = await response.json();

        return uploadInformations
}

async function uploadFile(file, uploadInformations, uploadEndpoint) {

    var body = new FormData()
    
    body.append('token', uploadInformations['data']['token']);
    body.append('file', file );
    
    
    const payload = {
        method: 'POST',
        body: body
    }

    const response = fetch(uploadEndpoint, payload).then((response) => response.json())
    
    return response
    
}
