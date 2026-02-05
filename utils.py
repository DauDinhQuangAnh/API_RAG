import os
import math
import uuid
import platform
import requests
import re


def process_batch(batch_df, model, collection):
    try:
        embeddings = model.encode(batch_df['chunk'].tolist())

        metadatas = [row.to_dict() for _, row in batch_df.iterrows()]

        batch_ids = [str(uuid.uuid4()) for _ in range(len(batch_df))]

        collection.add(
            ids=batch_ids,
            embeddings=embeddings,
            metadatas=metadatas
        )
    except Exception as e:
        if str(e) == "'NoneType' object has no attribute 'encode'":
            raise RuntimeError("Please set up the language model at section #1 before running the processing.")
        raise RuntimeError(f"Error saving data to Chroma for a batch: {str(e)}")

    
def divide_dataframe(df, batch_size):
    num_batches = math.ceil(len(df) / batch_size)
    return [df.iloc[i * batch_size:(i + 1) * batch_size] for i in range(num_batches)]

def clean_collection_name(name):
    cleaned_name = re.sub(r'[^a-zA-Z0-9_.-]', '', name)   # Step 1: Remove invalid characters
    cleaned_name = re.sub(r'\.{2,}', '.', cleaned_name)    # Step 2: Remove consecutive periods
    cleaned_name = re.sub(r'^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$', '', cleaned_name)  # Step 3: Remove leading/trailing non-alphanumeric characters

    return cleaned_name[:63] if 3 <= len(cleaned_name) <= 63 else None