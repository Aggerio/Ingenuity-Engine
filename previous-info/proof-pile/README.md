---
annotations_creators:
- no-annotation
language:
- en
language_creators:
- found
license: [apache-2.0]
multilinguality:
- monolingual
pretty_name: proof-pile
size_categories: []
source_datasets: []
tags:
- math
- mathematics
- formal-mathematics
task_categories:
- text-generation
task_ids:
- language-modeling
---

# Dataset Description
The `proof-pile` is a 13GB pre-training dataset of mathematical text that comprises 8.3 billion tokens (using the `gpt-neox` tokenizer). Models trained on this dataset are coming soon :) The dataset is composed of diverse sources of both informal and formal mathematics, namely
- ArXiv.math (10GB)
- Open-source math textbooks (50MB)
- Formal mathematics libraries (500MB)
    - Lean mathlib and other Lean repositories 
    - Isabelle AFP
    - Coq mathematical components and other Coq repositories 
    - HOL Light
    - set.mm
    - Mizar Mathematical Library
- Math Overflow and Math Stack Exchange (2.5GB)
- Wiki-style sources (50MB)
  - ProofWiki
  - Wikipedia math articles
- MATH dataset (6MB)

The construction of the dataset is reproducible using the code and instructions in the [proof-pile Github
repo](https://github.com/zhangir-azerbayev/proof-pile). 

# Supported Tasks
This dataset is intended to be used for pre-training and fine-tuning language models. We envision models trained on the `proof-pile` will have many downstream applications, including informal quantitative reasoning, formal theorem proving, semantic search for formal mathematics, and autoformalization. 

# Languages
All informal mathematics in the `proof-pile` is written in English and LaTeX (arXiv articles in other languages are filtered out using [languagedetect](https://github.com/shuyo/language-detection/blob/wiki/ProjectHome.md)). Formal theorem proving languages represented in this dataset are Lean 3, Isabelle, Coq, HOL Light, Metamath, and Mizar.
 
# Evaluation
The version of `set.mm` in this dataset has 10% of proofs replaced with the `?` character in order to preserve a validation and test set for Metamath provers pre-trained on the `proof-pile`. The precise split can be found here: [validation](https://github.com/zhangir-azerbayev/mm-extract/blob/main/valid_decls.json) and [test](https://github.com/zhangir-azerbayev/mm-extract/blob/main/test_decls.json). 
The Lean mathlib commit used in this dataset is `6313863`. Theorems created in subsequent commits can be used for evaluating Lean theorem provers. 

This dataset contains only the training set of the [MATH dataset](https://github.com/hendrycks/math). However, because this dataset contains ProofWiki, the Stacks Project, Trench's Analysis, and Stein's Number Theory, models trained on it cannot be evaluated on the [NaturalProofs dataset](https://github.com/wellecks/naturalproofs). 

# Data Preprocessing
This section describes any significant filtering and transformations made to various subsets of the data. 

**arXiv.math.**
The arXiv.math dataset is large, heterogeneous, and contains a great deal of noise. We used the following heuristics
when choosing which files from arXiv.math source folders to include in the dataset:
- Keep only files with a `.tex` extension.
- Only include files that use either a `utf-8/16/32` or `latin-1` text encoding. 
- Discard files that do not contain a part, chapter, section, sub...section, paragraph, or subparagraph heading. 
- Delete files that contain the keyword `gnuplot`. Gnuplot-latex is an old command line utility that generates blocks
  of entirely unintelligible source. 
- Include only articles in English, as determined by the [langdetect library](https://pypi.org/project/langdetect/). \n",
    "\n",
- Exclude files shorter than 280 characters (characters counted after substring removal described below).

In addition, we apply the following transformations to arXiv.math texts: 

- Delete everything outside of `\begin{document}` and `\end{document}`. 
- Delete everything including or after `\Refs`, `\begin{thebibliography}`, or `\begin{bibdiv}`
- Delete comments. 
- Any more than three consecutive newlines are replaced by three consecutive newlines. 
In [this notebook](https://github.com/zhangir-azerbayev/proof-pile/blob/main/analysis/arxiv_noisedetection.ipynb), we provide an analysis of the prevalence of noisy documents in the arXiv.math subset of the
proof-pile. 

**Stack Exchange.**
We only include questions that have at least 5 upvotes and an answer. We format Stack Exchange posts as follows
```
QUESTION [{num_upvotes} upvotes]: {text of question}

REPLY [{num_upvotes} votes]: {text of reply}

REPLY [{num_upvotes} votes]: {text of reply}

.
.
.
```

**set.mm.**
We converted `set.mm` into human-readable form by following the instructions in the [mm-extract repo](https://github.com/zhangir-azerbayev/mm-extract)

## Contributions
Authors: Zhangir Azerbayev, Edward Ayers, Bartosz Piotrowski. 

We would like to thank Jeremy Avigad, Albert Jiang, and Wenda Li for their invaluable guidance, and the Hoskinson Center for Formal Mathematics for its support. 
