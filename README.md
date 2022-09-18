# rdgen: LL(1) EBNF Recursive Descent Parser Generator

This is a parser generator for LL(1) EBNF grammars. It generates a predictive recursive descent parser in Python 3.10.

The interface of the generated parser and the expected interface are those dictated by CSC 453 at the University of Arizona when taught by Todd Proebsting.

The application can generate a parser, or it can generate random sentences in the language of a grammar.

```
$ python3 main.py -h
usage: main.py [-h] {create,examples} ...

positional arguments:
  {create,examples}
    create           create a parser
    examples         create a JSON file with example sentences

options:
  -h, --help         show this help message and exit
```

## Generating a Parser

```
$ python3 main.py create -h
usage: main.py create [-h] [--input INPUT] [--output OUTPUT] [--verbose]

options:
  -h, --help       show this help message and exit
  --input INPUT    input file
  --output OUTPUT  output file
  --verbose        verbose output
```

If the grammar has LL(1) conflicts, they will be noted in the generated Python file with the word, `AMBIGUOUS`.

## Generating Example Sentences

The generated sentences are in JSON format.




```
$ python3 main.py examples -h
usage: main.py examples [-h] [--input INPUT] [--output OUTPUT]
                        [--quantity QUANTITY] [--limit LIMIT]

options:
  -h, --help           show this help message and exit
  --input INPUT        input file
  --output OUTPUT      output file
  --quantity QUANTITY  quantity of output needed
  --limit LIMIT        limit on number of iterations
```

**NOTE:** The generated sentences contain the names of tokens, not specific values.  For instance, it may generate `INT` instead of an actual integer literal (e.g., `314`).

The unix `sed` utility can help convert the generated sentences to have appropriate literal values.  E.g., the following will convert all `INT` tokens to `314` in the file `examples.json`:

```
$ sed 's/INT/314/g' examples.json
```