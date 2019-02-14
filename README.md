# Haxe bindings generator for Phaser 3

This Python script generates Haxe bindings for Phaser 3.X. Please note that bindings generated can contains errors.
It's highly recommanded to understand how bindings works to use that. If you have a compilation error (function call mismatch for example), check if it's not a bad definition in the bindings.

The script contains multiple hacks for very specific situations. There is probably other issues.

The positive part is that we used that script for a LudumDare and it was usable. Fixes we had to do in the bindings have now been corrected in the script.

## how to use it

The script use the JSON output of JSDOC.

```
node node_modules/jsdoc/jsdoc.js -X -r phaser/src > phaser_jsdoc.json
python3 generate_bindings.py phaser_jsdoc.json output
```

