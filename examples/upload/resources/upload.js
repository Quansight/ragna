
function upload() {
                        
    var files = $$$("input#fileUpload")[0].files;
    
    Array.from(files).forEach(file => {

        getUploadInformations(file).then(
                function(uploadInformations) { 
                        uploadFile(file,uploadInformations)
                }
        );
    });
    
}
 
async function getUploadInformations(file) {
        const response = await fetch("http://localhost:8000/get-upload-information?filename="+file.name );
        const uploadInformations = await response.json();
        return uploadInformations
}

async function uploadFile(file, uploadInformations) {

    // Can we get raw bytes here to avoid coding ping pong?
    const reader = new FileReader();
    reader.addEventListener('load', (event) => {
        fileData = event.target.result;

        // Let's not hard code this here, since this is fundamental
        const url = "http://localhost:8000/upload-document";
        
        var body = new FormData()
        
        body.append('file', fileData);
        body.append('filename', file.name);
        body.append('upload_hash', uploadInformations['upload_hash']);
        body.append('timestamp', uploadInformations['timestamp']);

        const payload = {
            method: 'POST',
            body: body
        }

        const response = fetch(url, payload)
        
        return response
    });

    reader.readAsDataURL(file);
}
