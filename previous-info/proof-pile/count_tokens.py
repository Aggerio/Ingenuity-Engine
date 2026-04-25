from datasets import load_dataset
from itertools import islice
import sys
import time
from tqdm import tqdm
from transformers import AutoTokenizer
from itertools import islice
import json

NUM_PROC = 12

dataset = load_dataset("hoskinson-center/proof-pile")
tokenizer = AutoTokenizer.from_pretrained("EleutherAI/gpt-neox-20B")

def length(example):
    return {"length": [len(x) for x in tokenizer(example["text"])["input_ids"]]}

dataset = dataset.map(length, batched=True, num_proc=NUM_PROC)

stats = dict()

for x in tqdm(dataset["train"]):
    meta = json.loads(x["meta"])

    if "config" in meta.keys():
        config = meta["config"]
    elif "set_name" in meta.keys(): 
        config = meta["set_name"]
    elif "subset_name" in meta.keys():
        path = meta["file"]
        config = path[:path.index("/")]
    else:
        print(x)
        raise KeyError()

    if config not in stats.keys():
        stats[config] = dict()
        stats[config]["bytes"] = 0 
        stats[config]["tokens"] = 0

    stats[config]["bytes"] += len(x["text"].encode("utf-8"))
    stats[config]["tokens"] += x["length"]


print(json.dumps(stats, indent=2))
print("saving stats...")

with open("stats.json", "w") as f: 
    f.write(json.dumps(stats, indent=2))
