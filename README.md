# rdgen: LL(1) EBNF Recursive Descent Parser Generator

This is a parser generator for LL(1) EBNF grammars. It generates a predictive recursive descent parser in Python 3.10.

The interface of the generated parser and the expected interface are those dictated by CSC 453 during Fall 2022.

The application can generate a parser, or it can generate random sentences in the language of a grammar.

## Input Specification

This is the EBNF grammar for the EBNF grammar to be processed by rdgen:

```
grammar: production { production } .
production: ID ":" alternation "." .
alternation: sequence { "|" sequence } .
sequence: term { term } .
term: "(" alternation ")"
    | "{" alternation "}"
    | "[" alternation "]"
    | ID
    | STR
    .
```

Note the following:
1. A grammar must have at least one production.
2. The nonterminal of the first production is the start symbol.
3. Any symbol that isn't a nonterminal is treated as a terminal.
   * identifier symbols begin with a letter and then contain letters, digits, and underscores
   * string symbols begin and end with a double quote and contain any character except a double quote and newline.
4. `EOF` is not part of the grammar.
5. Only one production per nonterminal is allowed.
6. All right-hand sides must be non-empty.


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

If the grammar has LL(1) conflicts, they will be noted in the generated Python file with the word, "`AMBIGUOUS`".

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