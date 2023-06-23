from typing import Tuple, NamedTuple
import string

keywords = {"break", "continue"}

punctuation = {
    "{+",
    "+}",
    "=",
    "'",
    ".",
    ":",
    "[",
    "]",
    "(",
    ")",
    "{",
    "}",
    "|",
    "@",
    "!",
}

delimited = [
    ('"', '"', "STR", False),
    ("<<", ">>", "CODE", True),
    ("«", "»", "CODE", True),
    ("⟪", "⟫", "CODE", True),
]


class Token(NamedTuple):
    kind: str
    value: str
    line: int
    column: int


def tokenize(s: str) -> Tuple[list[Token], list[str]]:
    tokens: list[Token] = []
    pragmas: list[str] = []
    line = 1
    line_start = 0
    i = 0

    while i < len(s):
        if s[i] in string.whitespace:
            if s[i] == "\n":
                line += 1
                line_start = i
            i += 1
        elif s[i:].startswith("%%"):
            i += 2
            pstart: int = i
            while i < len(s) and s[i] != "\n":
                i += 1
            pragma: str = s[pstart:i]
            pragmas.append(pragma)
        elif s[i] == "#":
            i += 1
            while i < len(s) and s[i] != "\n":
                i += 1
        elif any(s[i:].startswith(d[0]) for d in delimited):
            for d in delimited:
                if s[i:].startswith(d[0]):
                    token_start = i
                    i += len(d[0])
                    while (
                        i < len(s)
                        and s[i] != "\n"
                        and not s[i:].startswith(d[1])
                    ):
                        i += 1
                    if not s[i:].startswith(d[1]):
                        raise Exception(f"Line {line}: missing delimiter")
                    i += len(d[1])
                    if d[3]:
                        value = s[token_start + len(d[0]) : i - len(d[1])]
                    else:
                        value = s[token_start:i]
                    tokens.append(
                        Token(
                            d[2],
                            value,
                            line,
                            token_start - line_start + 1,
                        )
                    )
                    line_start = i
                    break
        elif s[i] in string.ascii_letters:
            token_start = i
            i += 1
            while (
                i < len(s)
                and s[i] in string.ascii_letters + string.digits + "_"
            ):
                i += 1
            name = s[token_start:i]
            if name in keywords:
                kind = name
            else:
                kind = "ID"
            tokens.append(
                Token(
                    kind,
                    name,
                    line,
                    token_start - line_start + 1,
                )
            )

        else:
            found = False
            suffix = s[i:]
            for p in punctuation:
                if suffix.startswith(p):
                    tokens.append(Token(p, p, line, i - line_start + 1))
                    i += len(p)
                    found = True
                    break
            if not found:
                raise Exception(f"Invalid character {s[i]}")
    tokens.append(Token("EOF", "", line, i - line_start + 1))
    return tokens, pragmas


class Scanner:
    input: str
    tokens: list[Token]
    index: int
    pragmas: list[str]

    def __init__(self, input: str):
        self.input = input
        self.tokens, self.pragmas = tokenize(input)
        self.index = 0

    def peek(self) -> Token:
        return self.tokens[self.index]

    def consume(self) -> Token:
        ret: Token = self.tokens[self.index]
        self.index += 1
        return ret

    def match(self, type: str) -> Token:
        if self.peek().kind == type:
            return self.consume()
        raise Exception(f"Expected {type} got {self.peek()}")
