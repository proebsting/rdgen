# rdgen: Retargetable LL(1) EBNF Recursive Descent Parser Generator

This is a parser generator for LL(1) EBNF grammars. It generates a predictive recursive descent parser in Python 3.10.

The interface of the generated parser and the expected interface are those dictated by CSC 453 during Fall 2022.

The application can generate a parser, or it can generate random sentences in the language of a grammar.

## Input Specification

This is the EBNF grammar for the EBNF grammar to be processed by rdgen:

```
grammar: production { production } .
production: ID ":" alternation "." .
alternation: sequence { "|" sequence } .
sequence: { term } .
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
5. Multiple productions per nonterminal are allowed.  `rdgen` will simply merge them into one production.
6. While EBNF typically forbids empty sequences, `rdgen` allows them.  E.g., `foo: .` is allowed.


## Generating a Parser

```
$ python3 main.py create --help
usage: main.py create [-h] [--input INPUT] [--output OUTPUT] [--verbose] [--decorate]

options:
  -h, --help       show this help message and exit
  --input INPUT    input file
  --output OUTPUT  output file
  --verbose        verbose output
  --decorate       decorate
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

# NEW STUFF

The following has been implemented but is throughly untested.  (Note that "throughly untested" is even less tested than "not thoroughly tested.")  USE AT YOUR OWN RISK.

`rdgen` now supports the ability to add Python code in the grammar:

### Creating code

To cause code to be generated, add the `--decorate` option to the `create` command.  

### Computing Values

Every sequence of elements of the right-hand side of a production represents a value.  It can be specified in two different ways.  In order, these are the ways (the first applicable rule is used):

1. whatever is followed by a `=`
   1. `= <<`*expr*`>>` produces, where *expr* is a valid one-line Python expression.
   2. the value of the only element in the sequence preceded by an `=`
5. the value of the singleton term

By default, the value of `[` *sequence* `]` is `None` if the optional sequence isn't parsed, but it's the value of the sequence if it is parsed.  This can be overridden by putting `!` after the `]`.

By default, the value of `{` *sequence* `}` is a list of the values of the elements in the sequence.  This can be overridden by putting `!` after the `}`.

The value *alpha* `|` *beta* is the value of *alpha* if *alpha* is parsed, and the value of *beta* if *alpha* isn't parsed.

The value of `(` *sequence* `)` is the value of the sequence.  Parentheses are needed if you want to name the value of a sequence.  E.g., `(`*sequence*`)`'`foo` puts the value of *sequence* into a local variable, `foo`, in the emitted routine.

### Naming values

The value of a term can be named by following it with `'`*id* where *id* is an identifier.  

That name can then be used in the code of the production.

### Other code

Code put before the first production is emitted prior to the generated parser.

### Code in the grammar

Code in the grammar is anything found between

*  `<<` and `>>`, or
* `«` and  `»`, or
* `⟪` and `⟫`.

(There's no fancy escaping, so pick your chevrons wisely.)

The code is emitted after being stripped of leading and trailing whitespace.

