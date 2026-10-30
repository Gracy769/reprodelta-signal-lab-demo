# Signal Lab: ReproDelta demo repository

This is a small scientific Python project with four intentionally separate pull
requests. It lets a presenter show both outcomes ReproDelta currently supports:
a **paired NumPy replay** for an isolated version change, and a **diff-only
review** for ordinary application code changes.

The classifier in `fixture/project/pipeline.py` is ReproDelta's constructed
demonstration kernel. It illustrates NumPy scalar-promotion behavior; it is not
an independently observed research defect. The three application PRs add
substantial code around the classifier without claiming that ReproDelta ran it.

## Demo sequence

1. Sign in with GitHub on the
   [ReproDelta app](https://reprodelta-web-production.up.railway.app/) and
   connect this public repository. GitHub OAuth currently finishes on that
   domain; a Cloudflare-domain visit does not share its sign-in cookie.
2. Open PR **#1, NumPy 2.0 upgrade**. It changes only `requirements.txt` from
   `numpy==1.26.4` to `numpy==2.0.2` while the trusted kernel stays byte-identical.
   This is the one PR that can enter ReproDelta's curated paired-run path.
3. Open the other three PRs. They change application code. ReproDelta should
   show their changed files and limitations as **diff review only**. It does not
   execute arbitrary repository code from those PRs.

Each PR is independent and targets `main`; none needs to be merged to run the
demo. PR descriptions include the specific files and expected review mode.

## Run locally

Use Python 3.12. Install the requirements in a fresh virtual environment and
run `python run_example.py` or `python -m unittest discover -s tests -v`.
Switching to PR #1 requires a fresh environment because its NumPy pin changes.

The code is MIT licensed. No credentials or external services are required.
