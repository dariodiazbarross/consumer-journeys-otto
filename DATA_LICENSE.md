# Data license and attribution

The **OTTO Recommender Systems Dataset** is released under [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/), as stated by the [official OTTO repository](https://github.com/otto-de/recsys-dataset#license). OTTO's repository code has a separate MIT license; these are not interchangeable.

**Dataset authors:** Philipp Normann, Sophie Baumeister and Timo Wilm (2023).  
**Title:** OTTO Recommender Systems Dataset: A real-world e-commerce dataset for session-based recommender systems research.  
**Publisher:** Kaggle. **DOI:** [10.34740/KAGGLE/DSV/4991874](https://doi.org/10.34740/KAGGLE/DSV/4991874).

Credit the authors, link to the source and license, and indicate changes when redistributing or adapting the data. Do not imply endorsement. The license does not remove privacy or other applicable rights.

This project converts JSONL to Parquet, constructs timestamp-block prefixes and future target sets, aggregates historical signals and reports derived analyses. These transformations are changes by this project, not part of the original dataset release.

Raw and event-level data are **not redistributed** in this Git repository. Derived aggregate tables/figures retain source attribution and are shared under CC BY 4.0. Original analysis code and original explanatory prose use the repository's MIT license, without relicensing source material.

