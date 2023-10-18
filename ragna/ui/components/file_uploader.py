import json

import param
from panel.reactive import ReactiveHTML
from panel.widgets import Widget


class FileUploader(ReactiveHTML, Widget):
    file_list = param.List(default=["test", "test2"])
    file_list_html = param.String(default="")

    custom_js = param.String(default="")
    uploaded_documents_json = param.String(default="")

    title = param.String(default="")

    def __init__(self, user, informations_endpoint, upload_endpoint, **params):
        super().__init__(**params)

        self.user = user
        self.informations_endpoint = informations_endpoint
        self.upload_endpoint = upload_endpoint

        self.after_upload_callback = None

        # self.param.watch(self.did_change_value_input, ["value_input"])

    @param.depends("file_list", watch=True)
    def update_file_list_html(self):
        self.file_list_html = "<br />\n".join([f["name"] for f in self.file_list])
        print(self.file_list_html)
        return

    @param.depends("uploaded_documents_json", watch=True)
    def did_finish_upload(self):
        if self.after_upload_callback is not None:
            self.after_upload_callback(json.loads(self.uploaded_documents_json))

    def perform_upload(self, event=None, after_upload_callback=None):
        self.after_upload_callback = after_upload_callback

        final_callback_js = """
            var final_callback = function(uploaded_documents) {
                self.get_uploaded_documents_json().innerText = JSON.stringify(uploaded_documents);
            };

        """
        self.custom_js = (
            final_callback_js
            + f""" upload( self.get_upload_files(),  '{self.user}', '{self.informations_endpoint}', '{self.upload_endpoint}', final_callback) """
        )

    _child_config = {
        "custom_js": "template",
        "uploaded_documents_json": "template",
        "file_list_html": "model",  # literal template
    }

    _template = """
            <style>
                :host {
                background-color: red;
                }
                
            </style>
            <script>
                                                                    
                var scr = document.createElement("script");
                scr.src = "/resources/upload.js" + "?ts=" + new Date().getTime();
                document.getElementsByTagName("head")[0].appendChild(scr);
                                                                
            </script>
            <div>
                <label>Select file to upload</label>
                    <input type="file" id="fileUpload" multiple="multiple" onchange="${script('file_input_on_change')}" /> 
            </div>
            <div>
                ${file_list_html}
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
            
        """,
        "file_input_on_change": """
            
            var new_file_list = Array.from(fileUpload.files).map(function(f) {
                new_f = {
                    "lastModified":f.lastModified ,
                    "name":f.name ,
                    "size":f.size ,
                    "type":f.type ,
                };

                console.log(new_f);
                return new_f;
            });
            
            console.log("new file list", new_file_list);

            data.file_list = new_file_list;
           
            
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



        """,
        "remove": """  
                  
         """,
    }
