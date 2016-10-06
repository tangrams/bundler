# Tangram Bundler

Bundle a Tangram `.yaml` scene file (and the corresponding dependences and components) into a single `.zip` file.

### How to use?
First you need to install some Python dependences:

```bash
pip install pyyaml
```

and the you can excecute the script directly from this repository by doing:

```bash
python <(curl -s https://raw.githubusercontent.com/tangrams/bundler/master/bundler.py) 
```

Once the script runs will ask you for the main scene YAML file (the one that "rules" them all).