

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

/*
{
  "url": "http://127.0.0.1:31476/document",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyIjoiVXNlciIsImlkIjoiZjdiMWM5NmUtOGQwMy00NzVlLWIxOTctY2YzNzdmYmU4MDZmIiwiZXhwIjoxNjk3MDg1NTAwLjYxNDAzN30.4MSK3WfPMIWGlF5kQDuXIoqGII4h2dJXbQVLNrb2dw0"
  },
  "document": {
    "id": "f7b1c96e-8d03-475e-b197-cf377fbe806f",
    "name": "my_file.pdf"
  }
}
*/

        return uploadInformations
}

async function uploadFile(file, uploadInformations, uploadEndpoint) {

    // Let's not hard code this here, since this is fundamental
    //const url = "http://localhost:31476/upload-document";
    
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
