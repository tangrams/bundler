![](bundler.jpg)

# Tangram Bundler

Bundle a Tangram `.yaml` scene file (and the corresponding dependences and components) into a single `.zip` file.

## How to use it by installing it locally
Just do:

```bash
pip install tangram_bundler
tangram-bundle scene.yaml
```

## How to use it without installing locally

First you need to install some Python dependences:

```bash
pip install pyyaml
```

and the you can excecute the script directly from this repository by doing:

```bash
python <(curl -s https://raw.githubusercontent.com/tangrams/bundler/master/tangram_bundler/__init__.py)
```

Once the script runs will ask you for the main scene YAML file (the one that "rules" them all).


## Development

If you have the repo checked out and have made local modifications you'd like to test, run:

```bash
python setup.py install
```

Similarly, if you'd like to remove the library:

```bash
pip uninstall tangram_bundler
```
