import typing
import string
import pprint

punctuation = {".", ":", "[", "]", "(", ")", "{", "}", "|"}


class Token(typing.NamedTuple):
    kind: str
    value: str
    line: int
    column: int


def tokenize(s: str) -> list[Token]:
    tokens: list[Token] = []
    line = 1
    line_start = 0
    i = 0

    while i < len(s):
        if s[i] in string.whitespace:
            if s[i] == "\n":
                line += 1
                line_start = i
            i += 1
        elif s[i] == "#":
            i += 1
            while i < len(s) and s[i] != "\n":
                i += 1
        elif s[i] == '"':
            token_start = i
            i += 1
            while i < len(s) and s[i] != '"' and s[i]:
                i += 1
            if s[i] != '"':
                raise Exception("unterminated string")
            i += 1
            tokens.append(
                Token("STR", s[token_start:i], line, token_start - line_start + 1)
            )
            line_start = i
        elif s[i] in string.ascii_letters:
            token_start = i
            i += 1
            while i < len(s) and s[i] in string.ascii_letters + string.digits + "_":
                i += 1
            tokens.append(
                Token("ID", s[token_start:i], line, token_start - line_start + 1)
            )
        elif s[i] in punctuation:
            tokens.append(Token(s[i], s[i], line, i - line_start + 1))
            i += 1
        else:
            raise Exception(f"Invalid character {s[i]}")
    tokens.append(Token("EOF", "", line, i - line_start + 1))
    return tokens


class Scanner:
    def __init__(self, input: str):
        self.input = input
        self.tokens = tokenize(input)
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
