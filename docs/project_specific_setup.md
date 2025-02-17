## Install system-level dependencies with [homebrew](https://brew.sh/)

```sh
# brew install wkhtmltopdf
```

## gcloud setup

Install [gcloud as per these instructions](https://cloud.google.com/sdk/docs/install).

Run `gcloud init` to create a new named configuration. Unless it exists already, create a new
configuration as required, e.g. `IRIS-data-cleanser`. This configuration can be activated at any
point, for example:

```sh
gcloud config set project IRIS-data-cleanser

# Top tip: install tldr to get quick help with gcloud commands!
# https://dbrgn.github.io/tealdeer/
brew install tealdeer
tldr gcloud
```


## Jupyter kernel

```sh
python -m ipykernel install --user --name iris-data-cleanser --display-name "Python (iris-data-cleanser)"
```
