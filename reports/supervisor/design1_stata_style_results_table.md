# Design 1 Stata-Style Regression Table

Outcome variables are quarterly publication count and an indicator for any publication.
The reported coefficient is `Treated x Post` from the incumbent-project DID.
Application-clustered standard errors are in parentheses.

## Panel A. Q0: Application FE + calendar-quarter FE

| Outcome             | Publication count | Publication count | Any publication | Any publication |
| ------------------- | ----------------- | ----------------- | --------------- | --------------- |
| Control definition  | C05               | C06               | C05             | C06             |
| Treated x Post      | 0.015             | -0.021            | -0.002          | -0.016          |
|                     | (0.025)           | (0.024)           | (0.012)         | (0.012)         |
| Observations        | 51,515            | 52,034            | 51,515          | 52,034          |
| Applications        | 3,455             | 3,488             | 3,455           | 3,488           |
| Treated apps        | 3,324             | 3,191             | 3,324           | 3,191           |
| Control apps        | 131               | 297               | 131             | 297             |
| Application FE      | Yes               | Yes               | Yes             | Yes             |
| Calendar-quarter FE | Yes               | Yes               | Yes             | Yes             |
| Project-age-bin FE  | No                | No                | No              | No              |
| SE clustered by     | Application       | Application       | Application     | Application     |
| Pretrend p-value    | 0.079             | 0.070             | 0.201           | 0.156           |

## Panel B. Q1: Q0 + project-age-bin FE

| Outcome             | Publication count | Publication count | Any publication | Any publication |
| ------------------- | ----------------- | ----------------- | --------------- | --------------- |
| Control definition  | C05               | C06               | C05             | C06             |
| Treated x Post      | 0.025             | -0.034            | 0.003           | -0.024**        |
|                     | (0.024)           | (0.023)           | (0.012)         | (0.012)         |
| Observations        | 51,515            | 52,034            | 51,515          | 52,034          |
| Applications        | 3,455             | 3,488             | 3,455           | 3,488           |
| Treated apps        | 3,324             | 3,191             | 3,324           | 3,191           |
| Control apps        | 131               | 297               | 131             | 297             |
| Application FE      | Yes               | Yes               | Yes             | Yes             |
| Calendar-quarter FE | Yes               | Yes               | Yes             | Yes             |
| Project-age-bin FE  | Yes               | Yes               | Yes             | Yes             |
| SE clustered by     | Application       | Application       | Application     | Application     |
| Pretrend p-value    | 0.079             | 0.070             | 0.201           | 0.156           |

Notes: All specifications use the fixed 6,935 matched-project universe and the post-entry risk-set panel.
The post period treats 2024Q3 as post. Stars follow the Stata/esttab convention: * p<0.10, ** p<0.05, *** p<0.01.
C06 is the broadest provisional control sensitivity definition; it should not be interpreted as a finalized clean control group.
