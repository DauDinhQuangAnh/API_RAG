def vector_search(model, query, collection, columns_to_answer, number_docs_retrieval):
    query_embeddings = model.encode([query])
    search_results = collection.query(
        query_embeddings=query_embeddings, 
        n_results=number_docs_retrieval)  
    search_result = ""
    metadatas = search_results['metadatas']
    i = 0
    for meta in metadatas[0]:
        i += 1
        search_result += f"\n{i})"
        for column in columns_to_answer:
            if column in meta:
                search_result += f" {column.capitalize()}: {meta.get(column)}"

        search_result += "\n"
    return metadatas, search_result