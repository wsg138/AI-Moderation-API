# W23 Codacy false-positive record

These findings are documented individually rather than suppressed by a repository-wide analyzer exclusion. Each import is an experiment/test dependency that is pinned and installed by the W23 GitHub Actions workflow, but Codacy Prospector's Pyright environment does not install those optional dependencies. The corresponding source line uses a narrow `pyright: ignore[reportMissingImports]` annotation only for that import.

| Codacy issue | File | Import | Why false positive |
| --- | --- | --- | --- |
| `58cfbe830662cd0caf06298aa6d947b6` | `workers/w23/modeling.py` | `numpy` | Installed by pinned W12 evidence requirements used by W23. |
| `71264a6d8c6a473744fa4c6974bab58e` | `workers/w23/modeling.py` | `sklearn.feature_extraction.text` | scikit-learn is installed by the W23 experiment workflow. |
| `a1aa95b0b619654d6c4123169e1a9652` | `workers/w23/modeling.py` | `sklearn.linear_model` | scikit-learn is installed by the W23 experiment workflow. |
| `29d52ed75719078f43b04e440cbac2a5` | `workers/w23/modeling.py` | `sklearn.model_selection` | scikit-learn is installed by the W23 experiment workflow. |
| `6694f45aff2886942f0dbc2576899eb4` | `workers/w23/modeling.py` | `sklearn.pipeline` | scikit-learn is installed by the W23 experiment workflow. |
| `60924c142014f89afadb2ea377da519e` | `workers/w23/meta.py` | `numpy` | Installed by pinned W12 evidence requirements used by W23. |
| `3423d4e2caa99c94868e94b731127f9b` | `workers/w23/meta.py` | `sklearn.linear_model` | scikit-learn is installed by the W23 experiment workflow. |
| `a1211d070061a3b714a3934df4f6607e` | `workers/w23/meta.py` | `sklearn.pipeline` | scikit-learn is installed by the W23 experiment workflow. |
| `cb823e1168f6d535085389fe9ddd57c6` | `workers/w23/meta.py` | `sklearn.preprocessing` | scikit-learn is installed by the W23 experiment workflow. |
| `f4f498c567868355d32536c73e6354` | `workers/w23/bert_support.py` | `numpy` | Installed by pinned W12 evidence requirements used by W23. |
| `532069b9ec06bd2f5ab4a339da65ca86` | `workers/w23/bert_support.py` | `torch` | PyTorch is installed by the pinned W12 evidence requirements used by W23 OOF jobs. |
| `6d036f749327565d6a5223176368685e` | `workers/w23/bert_support.py` | `sklearn.model_selection` | scikit-learn is installed by the W23 experiment workflow. |
| `ddaca8be20c6ac537603146be8c2e46f` | `workers/w23/bert_support.py` | `torch.utils.data` | PyTorch is installed by the pinned W12 evidence requirements used by W23 OOF jobs. |
| `5787eba1af16559d676c56e82c6e6b69` | `workers/w23/features.py` | `numpy` | Installed by pinned W12 evidence requirements used by W23. |
| `111b749ec478e8eb8fa1ff561f66f8e4` | `workers/w23/rules.py` | `numpy` | Installed by pinned W12 evidence requirements used by W23. |
| `8f9d1e00d464cbb63d3637ab08564e4b` | `tests/test_w23.py` | `pytest` | pytest is installed by the repository development dependency set in both local and CI test jobs. |

The three non-import Codacy findings from the first PR analysis were treated as valid: two Lizard CCN findings in `metrics.py` were refactored below the project limit, and the Opengrep implicit-list-string-concatenation finding in `reporting.py` was rewritten explicitly.
