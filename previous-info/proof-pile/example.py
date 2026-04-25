from datasets import load_dataset
from itertools import islice
import sys
import time
from tqdm import tqdm

dataset = load_dataset("./proof-pile.py", "default")

size = dataset["train"].dataset_size / 2**30
print(f"{size} GB TRAIN TOTAL")
print(dataset)
for x in tqdm(dataset["train"]): 
    print("EXAMPLE INSTANCE (trimmed):")
    print(x["text"][:100])
    break

then = time.time()
for x in tqdm(dataset["train"]):
    pass
now = time.time()
print(f"{size} GB TRAIN TOTAL")
print(f"TRAVERSED IN {now-then} SECONDS")

size += dataset["validation"].dataset_size/2**30 + dataset["test"].dataset_size/2**30
print(f"{size} GB TOTAL (TRAIN, VAL, TEST)")

