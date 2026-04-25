# Copyright 2020 The HuggingFace Datasets Authors and the current dataset script contributor.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""A dataset of high quality mathematical text."""


import csv
import json
import os

import itertools
from itertools import islice

import datasets


# TODO: Add BibTeX citation
# Find for instance the citation on arxiv or on the dataset repo/website
_CITATION = """\
@InProceedings{huggingface:dataset,
title = {proof-pile},
author={Zhangir Azerbayev, Edward Ayers, Bartosz Piotrowski
},
year={2022}
}
"""

# TODO: Add description of the dataset here
# You can copy an official description
_DESCRIPTION = """\
A dataset of high quality mathematical text. """
_HOMEPAGE = "https://huggingface.co/datasets/hoskinson-center/proof-pile"

# TODO: Add the licence for the dataset here if you can find it
_LICENSE = "MIT"

# TODO: Add link to the official dataset URLs here
# The HuggingFace Datasets library doesn't host the datasets but only points to the original files.
# This can be an arbitrary nested dict/list of URLs (see below in `_split_generators` method)
_URLS = {
    "first_domain": "https://huggingface.co/datasets/hoskinson-center/proof-pile",
}


# TODO: Name of the dataset usually match the script name with CamelCase instead of snake_case
class ProofPile(datasets.GeneratorBasedBuilder):
    """A dataset of high quality mathematical text"""

    VERSION = datasets.Version("1.1.0")

    # This is an example of a dataset with multiple configurations.
    # If you don't want/need to define several sub-sets in your dataset,
    # just remove the BUILDER_CONFIG_CLASS and the BUILDER_CONFIGS attributes.

    # If you need to make complex sub-parts in the datasets with configurable options
    # You can create your own builder configuration class to store attribute, inheriting from datasets.BuilderConfig
    # BUILDER_CONFIG_CLASS = MyBuilderConfig

    # You will be able to load one or the other configurations in the following list with
    # data = datasets.load_dataset('my_dataset', 'first_domain')
    # data = datasets.load_dataset('my_dataset', 'second_domain')
    BUILDER_CONFIGS = [
    datasets.BuilderConfig(name="default", version=VERSION, description=""),
    ]


    def _info(self):
        # TODO: This method specifies the datasets.DatasetInfo object which contains informations and typings for the dataset
        features = datasets.Features(
            {
                "text": datasets.Value("string"),
                "meta": datasets.Value("string")
                # These are the features of your dataset like images, labels ...
            }
        )
        return datasets.DatasetInfo(
            # This is the description that will appear on the datasets page.
            description=_DESCRIPTION,
            # This defines the different columns of the dataset and their types
            features=features,  # Here we define them above because they are different between the two configurations
            # If there's a common (input, target) tuple from the features, uncomment supervised_keys line below and
            # specify them. They'll be used if as_supervised=True in builder.as_dataset.
            # supervised_keys=("sentence", "label"),
            # Homepage of the dataset for documentation
            homepage=_HOMEPAGE,
            # License for the dataset if available
            license=_LICENSE,
            # Citation for the dataset
            citation=_CITATION,
        )

    def _split_generators(self, dl_manager):
        # TODO: This method is tasked with downloading/extracting the data and defining the splits depending on the configuration
        # If several configurations are possible (listed in BUILDER_CONFIGS), the configuration selected by the user is in self.config.name

        # dl_manager is a datasets.download.DownloadManager that can be used to download and extract URLS
        # It can accept any type or nested list/dict and will give back the same structure with the url replaced with path to local files.
        # By default the archives will be extracted and a path to a cached folder where they are extracted is returned instead of the archive

            train_files = [dl_manager.download_and_extract(f"train/proofpile_train_{i}.jsonl.gz") for i in range(21)]
            val_files = [dl_manager.download_and_extract("dev/proofpile_dev.jsonl.gz")]
            test_files = [dl_manager.download_and_extract("test/proofpile_test.jsonl.gz")]
 
            return [
                datasets.SplitGenerator(
                    name=datasets.Split.TRAIN,
                    # These kwargs will be passed to _generate_examples
                    gen_kwargs={
                        "data_files": train_files,
                    },
                ),
                datasets.SplitGenerator(
                    name=datasets.Split.VALIDATION, 
                    # These kwargs will be passed to _generate_examples
                    gen_kwargs={
                        "data_files": val_files,
                    },
                ),
                datasets.SplitGenerator(
                    name=datasets.Split.TEST, 
                    gen_kwargs={
                        "data_files": test_files, 
                    }, 
                ), 
            ]
    # method parameters are unpacked from `gen_kwargs` as given in `_split_generators`
    def _generate_examples(self, data_files):
        # TODO: This method handles input defined in _split_generators to yield (key, example) tuples from the dataset.
        # The `key` is for legacy reasons (tfds) and is not important in itself, but must be unique for each example.
        key = 0 
        for name in data_files: 
            with open(name) as f: 
                instances = [json.loads(x) for x in f.readlines() if x]
            for instance in instances: 
                yield key, {"text": instance["text"], 
                        "meta": json.dumps(instance["meta"])}
                key += 1 
