# dst-causal-proof-template
A template for causal proof studies. It is recommended to have one repo per client.

# Quick start

Create a Python environment using
```sh 
pipenv install
```
and set-up a new study folder under `studies` to host your work. You can use [studies/demo](studies/demo) as a template. 
Examples on the different methodologies available are found under [examples](examples) or under the official causal-proof library [dst-python-causal-inference/examples](https://github.com/CroudTech/dst-python-causal-inference/tree/main/examples).


--- 

# Setup


## Dependencies

- This repo relies on Croud `causalinf` library. At the time of writing, this library supports python >3.10.8 only - so ensure you use this runtime. To manage multiple environment, we recommend using [`pyenv`](https://github.com/pyenv/pyenv#getting-pyenv).

- Some of the scripts in this repo may require access to GCP (e.g. get data from BigQuery). To do so, ensure you are authenticated into google CLI. You can do so by running the following commands (and following instructions):
    ```sh
    gcloud auth login

    gcloud auth application-default login \
   --scopes=openid,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/sqlservice.login,https://www.googleapis.com/auth/drive
    ```


## Install

1. The repository requires the Causal Inference library: `https://github.com/CroudTech/dst-python-causal-inference`. This is automatically downloaded using `pipenv` by running:
    ```sh
    export PIPENV_VENV_IN_PROJECT=1   # optional. Tells pipenv to create the environemnt into a local folder .env
    pipenv install
    ```

## Usage

- From terminal, source python environments:
    ```sh 
    pipenv shell
    ```

<!-- - To test it's all ok, run `pytest`. Ensure all tests are successful. -->

- You can now run from both terminal or inside a jupyter notebook. To use in a jupyter notebook, select as a kernel `.venv/bin/python`.


## Troubleshooting

- If installation fails, or `pipenv` installs an older version of `causalinf`, try:
    - deleting the `Pipfile.lock`, 
    - delete (if exists) any pipenv environment created so far (`pipenv --rm`) 
    - and try reinstalling (`pipenv install`).

- If issues persist, try cloning the `causalinf` git repository locally; next, change the `Pipfile` file to point to the folder where `causalinf` was cloned. This can be achieved by:

    a. Run the following
    ```sh 
    git clone --branch feature/initial-release --depth 1 git@github.com:CroudTech/dst-python-causal-inference.git .dst-python-causal-inference
    echo "causalinf library cloned"
    pipenv install
    rm -Rf .dst-python-causal-inference
    ```

    b. In `Pipfile`, modify the path for the `causalinf` file so as to point to the local folder. The Pipfile dependencies should look like this:
    ```py
    [packages]
    ipython = "*"
    causalinf = {path = "./.dst-python-causal-inference"}
    ```


- If installation fails, clone the `causalinf` library locally and add its location to the python path. This solution is not recommended.

    a. Clone the `causalinf` library:
    ```sh 
    git clone --branch feature/initial-release --depth 1 git@github.com:CroudTech/dst-python-causal-inference.git .dst-python-causal-inference
    echo "causalinf library cloned"
    ```

    b. Copy its Pipfile to root and install the virtual environment:
    ```sh 
    cp .dst-python-causal-inference/Pipfile ./Pipfile
    pipenv install
    ```

    c. Export the path ro `causalinf` as an environmental variable (add to `.env`):
    ```sh 
    export PATH_PYTHON_CAUSAL_INFERENCE=.dst-python-causal-inference
    ```

    d. In order to use `causalinf`, you will need to add the following to your scripts:
    ```python 
    import os, sys 
    sys.path.append(os.environ["PATH_PYTHON_CAUSAL_INFERENCE"])
    ```

