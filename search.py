def vector_search(model, query, collection, columns_to_answer, number_docs_retrieval):
    query_embeddings = model.encode([query])
    search_results = collection.query(
        query_embeddings=query_embeddings, 
        n_results=number_docs_retrieval)  
    search_result = ""
    metadatas = search_results['metadatas']
    if not metadatas or not metadatas[0]:
        return metadatas, search_result

    available_columns = set()
    for meta in metadatas[0]:
        if isinstance(meta, dict):
            available_columns.update(str(key).casefold() for key in meta.keys())

    missing_columns = [
        column
        for column in columns_to_answer
        if str(column).casefold() not in available_columns
    ]
    if missing_columns:
        missing_list = ", ".join(missing_columns)
        raise ValueError(f"Requested columns not found in collection metadata: {missing_list}")

    i = 0
    for meta in metadatas[0]:
        i += 1
        search_result += f"\n{i})"
        normalized_meta = {}
        if isinstance(meta, dict):
            normalized_meta = {
                str(key).casefold(): value
                for key, value in meta.items()
            }
        for column in columns_to_answer:
            normalized_column = str(column).casefold()
            if normalized_column in normalized_meta:
                search_result += f" {column}: {normalized_meta.get(normalized_column)}"

        search_result += "\n"
    return metadatas, search_result
