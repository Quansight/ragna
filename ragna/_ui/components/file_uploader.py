import json
import uuid

import param
from panel.reactive import ReactiveHTML
from panel.widgets import Widget


class FileUploader(ReactiveHTML, Widget):  # type: ignore[misc]
    allowed_documents = param.List(default=[])
    allowed_documents_str = param.String(default="")

    file_list = param.List(default=[])

    custom_js = param.String(default="")
    uploaded_documents_json = param.String(default="")

    title = param.String(default="")

    def __init__(self, allowed_documents, token, informations_endpoint, **params):
        super().__init__(**params)

        self.token = token
        self.informations_endpoint = informations_endpoint

        self.after_upload_callback = None

    def can_proceed_to_upload(self):
        return len(self.file_list) > 0

    @param.depends("allowed_documents", watch=True)
    def update_allowed_documents_str(self):
        if len(self.allowed_documents) == 1:
            self.allowed_documents_str = (
                "Only " + self.allowed_documents[0] + " files are allowed."
            )
        else:
            self.allowed_documents_str = "Allowed files : " + ", ".join(
                self.allowed_documents
            )

    @param.depends("uploaded_documents_json", watch=True)
    async def did_finish_upload(self):
        if self.after_upload_callback is not None:
            await self.after_upload_callback(json.loads(self.uploaded_documents_json))

    def perform_upload(self, event=None, after_upload_callback=None):
        self.after_upload_callback = after_upload_callback

        self.loading = True

        final_callback_js = """
            var final_callback = function(uploaded_documents) {
                self.get_uploaded_documents_json().innerText = JSON.stringify(uploaded_documents);
            };
        """

        # This is a hack to force the re-execution of the javascript.
        # If the whole javascript is the same, and doesn't change,
        # the panel widget is not re-renderer, and the upload function is not called.
        random_id = f" var random_id = '{str(uuid.uuid4())}';"

        self.custom_js = (
            final_callback_js
            + random_id
            + f"""upload( self.get_upload_files(),  '{self.token}', '{self.informations_endpoint}', final_callback) """
        )

    _child_config = {
        "custom_js": "template",
        "uploaded_documents_json": "template",
        "allowed_documents_str": "literal",
    }

    _template = """
            <style>
                :host {
                    width: 100%;
                    margin: 0px;
                    padding: 0px;
                }

                .fileUploadContainer {
                    height: 130px;
                }

                .fileUploadDropArea {
                    margin-left: 10px;
                    margin-right: 10px;
                    border: 1px dashed var(--accent-color);
                    border-radius: 5px;
                    height:100%;
                    display:flex;
                    text-align: center;
                    justify-content: center;
                    align-items: center;
                    flex-direction: column;
                }

                .fileUploadDropArea span.bold {
                    font-weight: bold;
                }

                .fileUploadDropArea img {
                    padding-bottom:5px;
                }

                .fileUploadDropArea.draggedOver {
                    border-width: 3px;
                }

                .fileUploadDropArea.uploaded {
                    height: calc(100% - 40px);
                }
                
                .fileUpload {
                    height: 100% !important;
                    position: absolute;
                    opacity: 0;
                }

                .fileListContainer {
                    display:flex;
                    flex-direction: row;
                    height: 44px;
                    overflow:scroll;
                    padding-top:14px;
                    padding-left:6px;
                }
                
                .chat_document_pill {
                    background-color: rgb(241,241,241);
                    margin-top:0px; 
                    margin-left: 5px;   
                    margin-right: 5px;
                    padding: 5px 15px;
                    border-radius: 10px;
                    color: var(--accent-color);
                    display: inline-table;
                    }
                
            </style>
            <script>
                                                                    
                var scr = document.createElement("script");
                scr.src = "/resources/upload.js" + "?ts=" + new Date().getTime();
                document.getElementsByTagName("head")[0].appendChild(scr);

            </script>
            <div id="fileUploadContainer" class="fileUploadContainer">
                <div id="fileUploadDropArea" class="fileUploadDropArea">
                    <img src="/imgs/cloud-upload.svg" width="24px" height="24px" />
                    <span><b>Click to upload</b> or drag and drop.<br /></span>
                    <div id='allowedDocuments'>
                        ${allowed_documents_str}
                    </div>
                    <input  type="file" 
                            name="fileUpload"
                            class="fileUpload" 
                            id="fileUpload" 
                            multiple="multiple" 
                            onchange="${script('file_input_on_change')}" /> 
                </div>
                <div id="fileListContainer" class="fileListContainer">
                    
                </div>
            </div>
            <div style="display:none;">
                <div id="custom_js_watcher">
                ${custom_js}
                </div>
                <div id="uploaded_documents_json_watcher">
                    
                </div>
            </div>
    """

    _scripts = {
        "after_layout": """ 
            self.update_layout();
        """,
        "update_layout": """ 

            
            if (data.file_list.length > 0) {
                fileUploadDropArea.classList.add("uploaded");
            } else {
                fileUploadDropArea.classList.remove("uploaded");
            }

            fileListContainer.innerHTML = "";

            data.file_list.forEach(function(f) {
                var pill = document.createElement("div");
                pill.classList.add("chat_document_pill");
                var fname = document.createTextNode(f.name);

                pill.appendChild(fname);
                fileListContainer.appendChild(pill);

            });

        """,
        "file_input_on_change": """
            
            
            var new_file_list = Array.from(fileUpload.files).map(function(f) {
                new_f = {
                    "lastModified":f.lastModified ,
                    "name":f.name ,
                    "size":f.size ,
                    "type":f.type ,
                };

                return new_f;
            });
            
            data.file_list = new_file_list;
            self.update_layout();
           
            
        """,
        "get_upload_files": """
            
            return fileUpload.files;
        """,
        "get_uploaded_documents_json": """
            return uploaded_documents_json_watcher;
        """,
        "render": """
            
            var MutationObserver = window.MutationObserver || window.WebKitMutationObserver || window.MozMutationObserver;
            var observer = new MutationObserver(function(mutationsList, observer) {
                    mutationsList.forEach(function(mutation){
                        if (mutation.type == 'characterData') {
                            eval(custom_js_watcher.innerText);
                        }
                        
                    });    

            });
            observer.observe(custom_js_watcher, {characterData: true, childList: true, attributes: true, subtree: true});


            var MutationObserver = window.MutationObserver || window.WebKitMutationObserver || window.MozMutationObserver;
            var observer = new MutationObserver(function(mutationsList, observer) {
                    mutationsList.forEach(function(mutation){
                        data.uploaded_documents_json = uploaded_documents_json_watcher.innerText
                    });    

            });
            observer.observe(uploaded_documents_json_watcher, {characterData: true, childList: true, attributes: true, subtree: true});


            fileUpload.addEventListener("dragenter", function(event){
                    fileUploadDropArea.classList.add("draggedOver");
            });

            fileUpload.addEventListener("dragleave", function(event){
                    fileUploadDropArea.classList.remove("draggedOver")
            });

            fileUpload.addEventListener("drop", function(event){
                    fileUploadDropArea.classList.remove("draggedOver")
                    event.preventDefault();
                    fileUpload.files = event.dataTransfer.files;
                    self.file_input_on_change();
            });

        """,
        "remove": """  
                  
         """,
    }
