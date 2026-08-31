# Data sources

Primary authority: [otto-de/recsys-dataset](https://github.com/otto-de/recsys-dataset), inspected at commit **f404284240ac654d0b924b2fabec0aea7b23f168**.

Use the official standalone **OTTO Recommender Systems Dataset, version 1**, published February 13, 2023; dataset ID 2895394, version ID 4991874. Do not substitute the competition's truncated test file.

- [Dataset page](https://www.kaggle.com/datasets/otto/recsys-dataset)
- [Version DOI](https://doi.org/10.34740/KAGGLE/DSV/4991874)
- [Versioned public ZIP download](https://www.kaggle.com/api/v1/datasets/download/otto/recsys-dataset?datasetVersionNumber=1)
- [File metadata](https://www.kaggle.com/api/v1/datasets/list/otto/recsys-dataset)
- [Version metadata](https://www.kaggle.com/api/v1/datasets/view/otto/recsys-dataset)

Files: otto-recsys-train.jsonl (11,307,535,945 bytes) and otto-recsys-test.jsonl (750,426,722 bytes), according to the official metadata. The acquisition manifest records the actual ZIP size, member sizes, SHA-256, source commit, URL and UTC download date. Ingestion also hashes each uncompressed member.

Acquisition uses the public download endpoint without a registration, competition acceptance, token or account. Redirect URLs are not stored because they contain temporary download signatures. The script streams the archive to disk; ingestion streams JSONL members without extracting the 12 GB of text.

The documented session is one user's activity within the train or test period, not a 30-minute visit. Official train and test users are disjoint. Documentation says training spans four weeks and test the next week; exact temporal boundaries are verified from timestamps before freezing the analysis.

Original fields are session, aid, ts and type. Type labels are clicks, carts and orders; milliseconds are verified from timestamp ranges. No prices, categories, product names, demographics, inventory or exposure logs are inferred.

See [DATA_LICENSE.md](DATA_LICENSE.md) for attribution, licensing and transformation disclosure. Only aggregate results and synthetic teaching examples are published.

