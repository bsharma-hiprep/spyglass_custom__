# Spyglass Custom

The Frank Lab's custom tools and tables for our Spyglass instance.

To use:

1. Install [Spyglass](https://lorenfranklab.github.io/spyglass/).
1. Fork this repository, and clone it.
1. Make install it as editable: `cd spyglass_custom; pip install -e .`
1. Decide your 'project name'.
   - If this work is unique to you, use your user name.
   - For any other name, you'll need to (a) talk to Chris about permissions and
     (b) set up your config with a 'database.prefix' (see `dj_local_conf_example.json`).
1. Make a new folder for your custom tables: `src/spyglass_custom/project-or-user/`.
   It is recommended that you copy the example in `cbroz1/template.py`
