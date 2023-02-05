import typing
import string

punctuation = {"=", "'", ".", ":", "[", "]", "(", ")", "{", "}", "|", "@", "!"}

delimited = [
    ('"', '"', "STR", False),
    ("<<", ">>", "CODE", True),
    ("«", "»", "CODE", True),
    ("⟪", "⟫", "CODE", True),
]


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
                        raise Exception("missing delimiter")
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
            tokens.append(
                Token(
                    "ID", s[token_start:i], line, token_start - line_start + 1
                )
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
