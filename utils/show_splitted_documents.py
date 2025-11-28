import json

def show_splitted_documents(policy_dodcument_context_splitted):
    documents_list = [
        {
            "page_content": doc.page_content,
            "metadata": doc.metadata
        } 
        for doc in policy_dodcument_context_splitted
    ]

    print(json.dumps(documents_list, indent=2))